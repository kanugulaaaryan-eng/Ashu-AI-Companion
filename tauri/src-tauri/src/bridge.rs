use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::{Manager, State};
use tokio::process::Command as TokioCommand;
use tokio::sync::Mutex as AsyncMutex;

pub struct BridgeManager {
    process: AsyncMutex<Option<tokio::process::Child>>,
    bridge_url: Mutex<String>,
    status: Mutex<BridgeStatus>,
}

#[derive(Clone, serde::Serialize, serde::Deserialize, Debug)]
pub struct BridgeStatus {
    pub running: bool,
    pub pid: Option<u32>,
    pub url: String,
    pub model: String,
    pub last_check: String,
    pub error: Option<String>,
}

impl Default for BridgeStatus {
    fn default() -> Self {
        Self {
            running: false,
            pid: None,
            url: "http://127.0.0.1:8765".to_string(),
            model: "nvidia/nemotron-3-ultra-550b-a55b".to_string(),
            last_check: "never".to_string(),
            error: None,
        }
    }
}

impl BridgeManager {
    pub fn new() -> Self {
        Self {
            process: AsyncMutex::new(None),
            bridge_url: Mutex::new("http://127.0.0.1:8765".to_string()),
            status: Mutex::new(BridgeStatus::default()),
        }
    }

    pub async fn start(&self) -> anyhow::Result<()> {
        self.stop().await?;

        let python_exe = Self::find_python()?;
        let script_path = Self::find_serve_script()?;
        let project_root = Self::find_project_root()?;

        {
            let mut status = self.status.lock().unwrap();
            status.running = false;
            status.error = None;
        }

        let mut cmd = TokioCommand::new(&python_exe);
        cmd.arg(&script_path)
            .arg("--nim")
            .arg("--host")
            .arg("127.0.0.1")
            .arg("--port")
            .arg("8765")
            .arg("--db")
            .arg("ashu_memory.db")
            .current_dir(&project_root)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .kill_on_drop(true);

        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
        }

        let mut child = cmd.spawn()?;

        let pid = child.id();
        let stdout = child.stdout.take();
        let stderr = child.stderr.take();

        {
            let mut status = self.status.lock().unwrap();
            status.running = true;
            status.pid = pid;
            status.last_check = chrono::Local::now().format("%H:%M:%S").to_string();
            status.error = None;
        }

        {
            let mut process = self.process.lock().await;
            *process = Some(child);
        }

        if let Some(stdout) = stdout {
            use tokio::io::{AsyncBufReadExt, BufReader};
            let reader = BufReader::new(stdout).lines();
            tokio::spawn(async move {
                let mut lines = reader;
                while let Ok(Some(line)) = lines.next_line().await {
                    println!("[bridge] {}", line);
                }
            });
        }

        if let Some(stderr) = stderr {
            use tokio::io::{AsyncBufReadExt, BufReader};
            let reader = BufReader::new(stderr).lines();
            tokio::spawn(async move {
                let mut lines = reader;
                while let Ok(Some(line)) = lines.next_line().await {
                    eprintln!("[bridge err] {}", line);
                }
            });
        }

        tokio::time::sleep(Duration::from_millis(2000)).await;
        self.check_health().await;

        Ok(())
    }

    pub async fn stop(&self) -> anyhow::Result<()> {
        let mut process = self.process.lock().await;
        if let Some(mut child) = process.take() {
            let _ = child.kill().await;
            let _ = child.wait().await;
        }

        let mut status = self.status.lock().unwrap();
        status.running = false;
        status.pid = None;
        Ok(())
    }

    pub async fn restart(&self) -> anyhow::Result<()> {
        self.stop().await?;
        self.start().await
    }

    pub async fn check_health(&self) -> anyhow::Result<bool> {
        let url = self.get_url();
        let client = reqwest::Client::new();

        let resp = client
            .get(format!("{}/v1/health", url))
            .timeout(Duration::from_secs(5))
            .send()
            .await;

        // First, get the response and parse JSON without holding the lock
        let (running, model, last_check, error) = match resp {
            Ok(resp) if resp.status().is_success() => {
                let json = resp.json::<serde_json::Value>().await.ok();
                let model = json.as_ref()
                    .and_then(|m| m.get("model"))
                    .and_then(|m| m.get("cloud"))
                    .and_then(|c| c.get("provider"))
                    .and_then(|p| p.as_str())
                    .unwrap_or("unknown")
                    .to_string();
                (true, Some(model), chrono::Local::now().format("%H:%M:%S").to_string(), None)
            }
            Ok(_) => {
                (false, None, chrono::Local::now().format("%H:%M:%S").to_string(), Some("Health check failed".to_string()))
            }
            Err(e) => {
                (false, None, chrono::Local::now().format("%H:%M:%S").to_string(), Some(e.to_string()))
            }
        };

        // Now acquire lock and update status
        let mut status = self.status.lock().unwrap();
        status.running = running;
        status.last_check = last_check;
        status.error = error;
        if let Some(m) = model {
            status.model = m;
        }
        Ok(running)
    }

    pub fn get_status(&self) -> BridgeStatus {
        self.status.lock().unwrap().clone()
    }

    pub fn get_url(&self) -> String {
        self.bridge_url.lock().unwrap().clone()
    }

    pub fn set_url(&self, url: String) {
        *self.bridge_url.lock().unwrap() = url;
    }

    fn find_python() -> anyhow::Result<PathBuf> {
        let candidates = vec![
            "python",
            "python3",
            "python.exe",
            "C:\\Python313\\python.exe",
            "C:\\Python312\\python.exe",
            "C:\\Python311\\python.exe",
            "C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Python\\Python313\\python.exe",
            "C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
            "C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Python\\Python311\\python.exe",
        ];

        for candidate in candidates {
            let expanded = shellexpand::env(candidate).ok().map(|s| s.into_owned()).unwrap_or(candidate.to_string());
            let path = PathBuf::from(&expanded);
            if path.exists() || Self::command_exists(&expanded) {
                return Ok(path);
            }
        }

        #[cfg(target_os = "windows")]
        {
            if let Ok(output) = Command::new("where").arg("python").output() {
                if output.status.success() {
                    let path = String::from_utf8_lossy(&output.stdout);
                    let first_line = path.lines().next().unwrap_or("");
                    if !first_line.is_empty() {
                        return Ok(PathBuf::from(first_line.trim()));
                    }
                }
            }
        }

        #[cfg(not(target_os = "windows"))]
        {
            if let Ok(output) = Command::new("which").arg("python3").output() {
                if output.status.success() {
                    let path = String::from_utf8_lossy(&output.stdout);
                    let first_line = path.lines().next().unwrap_or("");
                    if !first_line.is_empty() {
                        return Ok(PathBuf::from(first_line.trim()));
                    }
                }
            }
        }

        anyhow::bail!("Python not found. Please install Python 3.11+ and ensure it's in PATH.")
    }

    fn command_exists(cmd: &str) -> bool {
        Command::new(cmd).arg("--version").output().map(|o| o.status.success()).unwrap_or(false)
    }

    fn find_serve_script() -> anyhow::Result<PathBuf> {
        let current_exe = std::env::current_exe()?;
        let project_root = current_exe
            .parent()
            .and_then(|p| p.parent())
            .and_then(|p| p.parent())
            .and_then(|p| p.parent())
            .ok_or_else(|| anyhow::anyhow!("Could not find project root"))?;

        let serve_path = project_root.join("serve.py");
        if serve_path.exists() {
            return Ok(serve_path);
        }

        let mut current: Option<&std::path::Path> = Some(project_root.as_ref());
        while let Some(dir) = current {
            let serve = dir.join("serve.py");
            if serve.exists() {
                return Ok(serve);
            }
            current = dir.parent();
        }

        anyhow::bail!("serve.py not found in project")
    }

    fn find_project_root() -> anyhow::Result<PathBuf> {
        let current_exe = std::env::current_exe()?;
        let project_root = current_exe
            .parent()
            .and_then(|p| p.parent())
            .and_then(|p| p.parent())
            .and_then(|p| p.parent())
            .ok_or_else(|| anyhow::anyhow!("Could not find project root"))?;

        Ok(project_root.to_path_buf())
    }
}

fn find_python() -> anyhow::Result<PathBuf> {
    BridgeManager::find_python()
}

fn find_serve_script() -> anyhow::Result<PathBuf> {
    BridgeManager::find_serve_script()
}

fn find_project_root() -> anyhow::Result<PathBuf> {
    BridgeManager::find_project_root()
}

// Tauri commands
#[tauri::command]
pub async fn get_bridge_status(bridge: State<'_, Arc<BridgeManager>>) -> Result<BridgeStatus, String> {
    Ok(bridge.get_status())
}

#[tauri::command]
pub async fn restart_bridge(bridge: State<'_, Arc<BridgeManager>>) -> Result<BridgeStatus, String> {
    bridge.restart().await.map_err(|e| e.to_string())?;
    Ok(bridge.get_status())
}

#[tauri::command]
pub async fn set_bridge_url(bridge: State<'_, Arc<BridgeManager>>, url: String) -> Result<BridgeStatus, String> {
    bridge.set_url(url);
    bridge.restart().await.map_err(|e| e.to_string())?;
    Ok(bridge.get_status())
}
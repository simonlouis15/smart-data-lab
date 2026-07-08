use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use tauri::Manager;

// Embedded at compile time — no filesystem lookup needed at runtime.
const DEFAULT_CONFIG: &str = include_str!("../../backend/config/config.json");

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct PumpConfig {
    #[serde(rename = "Port")]
    pub port: String,
    #[serde(rename = "Pump Number")]
    pub pump_number: u32,
    #[serde(rename = "Flow Rate")]
    pub flow_rate: f64,
    #[serde(rename = "Baudrate")]
    pub baudrate: u32,
    #[serde(rename = "Bytesize")]
    pub bytesize: u8,
    #[serde(rename = "Parity")]
    pub parity: String,
    #[serde(rename = "Stopbits")]
    pub stopbits: f64,
    #[serde(rename = "Timeout")]
    pub timeout: f64,
    #[serde(rename = "Xonxoff")]
    pub xonxoff: bool,
    #[serde(rename = "Rtscts")]
    pub rtscts: bool,
    #[serde(rename = "Dsrdtr")]
    pub dsrdtr: bool,
    #[serde(rename = "WriteTimeout")]
    pub write_timeout: f64,
}

#[derive(Debug, Serialize)]
pub struct ImportResult {
    added: Vec<String>,
    skipped: Vec<String>,
    pumps: Value,
}

fn config_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let dir = app
        .path()
        .app_config_dir()
        .map_err(|e| format!("Failed to resolve app config dir: {e}"))?;

    if !dir.exists() {
        fs::create_dir_all(&dir)
            .map_err(|e| format!("Failed to create app config dir: {e}"))?;
    }

    Ok(dir.join("config.json"))
}

fn ensure_config_exists(app: &tauri::AppHandle) -> Result<(), String> {
    let target = config_path(app)?;
    if target.exists() {
        return Ok(());
    }

    serde_json::from_str::<Value>(DEFAULT_CONFIG)
        .map_err(|e| format!("Embedded default config.json is invalid JSON: {e}"))?;

    fs::write(&target, DEFAULT_CONFIG)
        .map_err(|e| format!("Failed to seed config.json at {:?}: {e}", target))?;

    Ok(())
}

fn read_config(app: &tauri::AppHandle) -> Result<Value, String> {
    let path = config_path(app)?;
    let data = fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read config at {:?}: {e}", path))?;
    serde_json::from_str(&data).map_err(|e| format!("Failed to parse config: {e}"))
}

fn write_config(app: &tauri::AppHandle, config: &Value) -> Result<(), String> {
    let path = config_path(app)?;
    let pretty = serde_json::to_string_pretty(config)
        .map_err(|e| format!("Failed to serialize config: {e}"))?;
    fs::write(&path, pretty).map_err(|e| format!("Failed to write config at {:?}: {e}", path))
}

fn pumps_object(config: &mut Value) -> Result<&mut serde_json::Map<String, Value>, String> {
    config
        .get_mut("Devices")
        .and_then(|d| d.get_mut("Pumps"))
        .and_then(|p| p.as_object_mut())
        .ok_or_else(|| "Pumps section not found in config".to_string())
}

#[tauri::command]
fn get_pump_configs(app: tauri::AppHandle) -> Result<Value, String> {
    let config = read_config(&app)?;
    config
        .get("Devices")
        .and_then(|d| d.get("Pumps"))
        .cloned()
        .ok_or_else(|| "Pumps section not found in config".to_string())
}

#[tauri::command]
fn pump_config_exists(app: tauri::AppHandle, name: String) -> Result<bool, String> {
    let config = read_config(&app)?;
    let pumps = config
        .get("Devices")
        .and_then(|d| d.get("Pumps"))
        .and_then(|p| p.as_object())
        .ok_or_else(|| "Pumps section not found in config".to_string())?;
    Ok(pumps.contains_key(&name))
}

#[tauri::command]
fn update_pump_config(
    app: tauri::AppHandle,
    name: String,
    pump: PumpConfig,
    original_name: Option<String>,
) -> Result<Value, String> {
    let mut config = read_config(&app)?;
    let pumps = pumps_object(&mut config)?;

    if let Some(orig) = &original_name {
        if orig != &name {
            pumps.remove(orig);
        }
    }

    let pump_value =
        serde_json::to_value(&pump).map_err(|e| format!("Failed to serialize pump: {e}"))?;
    pumps.insert(name, pump_value);

    write_config(&app, &config)?;
    get_pump_configs(app)
}

#[tauri::command]
fn delete_pump_config(app: tauri::AppHandle, name: String) -> Result<Value, String> {
    let mut config = read_config(&app)?;
    let pumps = pumps_object(&mut config)?;
    pumps.remove(&name);

    write_config(&app, &config)?;
    get_pump_configs(app)
}

/// Merges a batch of validated pumps into config.json. Any name that already
/// exists is skipped (not overwritten) to avoid clobbering an existing pump
/// via import — the caller can see what was skipped and rename/retry if needed.
#[tauri::command]
fn import_pump_configs(
    app: tauri::AppHandle,
    pumps: HashMap<String, PumpConfig>,
) -> Result<ImportResult, String> {
    let mut config = read_config(&app)?;
    let existing = pumps_object(&mut config)?;

    let mut added = Vec::new();
    let mut skipped = Vec::new();

    // Sort for deterministic, readable ordering in the result message.
    let mut entries: Vec<(String, PumpConfig)> = pumps.into_iter().collect();
    entries.sort_by(|a, b| a.0.cmp(&b.0));

    for (name, pump) in entries {
        if existing.contains_key(&name) {
            skipped.push(name);
            continue;
        }
        let pump_value = serde_json::to_value(&pump)
            .map_err(|e| format!("Failed to serialize pump \"{name}\": {e}"))?;
        existing.insert(name.clone(), pump_value);
        added.push(name);
    }

    write_config(&app, &config)?;
    let updated_pumps = get_pump_configs(app)?;

    Ok(ImportResult {
        added,
        skipped,
        pumps: updated_pumps,
    })
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            ensure_config_exists(&app.handle())?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            get_pump_configs,
            pump_config_exists,
            update_pump_config,
            delete_pump_config,
            import_pump_configs
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
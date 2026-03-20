use crate::error::JarvisResult;
use serde::Serialize;
use std::mem;
use windows::Win32::System::SystemInformation::{GlobalMemoryStatusEx, MEMORYSTATUSEX};
use windows::Win32::System::Power::GetSystemPowerStatus;
use windows::Win32::System::Power::SYSTEM_POWER_STATUS;
use windows::Win32::System::Threading::GetSystemTimes;
use windows::Win32::Foundation::FILETIME;

#[derive(Debug, Clone, Serialize)]
pub struct SystemMetrics {
    pub cpu_usage: f64,
    pub memory_usage: f64,
    pub battery_level: f64,
}

fn filetime_to_u64(ft: &FILETIME) -> u64 {
    ((ft.dwHighDateTime as u64) << 32) | (ft.dwLowDateTime as u64)
}

#[derive(Clone)]
pub struct SystemMonitor;

impl SystemMonitor {
    pub fn new() -> Self {
        Self
    }

    pub fn get_metrics(&self) -> JarvisResult<SystemMetrics> {
        let memory_usage = self.memory_usage()?;
        let battery_level = self.battery_level()?;
        let cpu_usage = self.cpu_usage().unwrap_or(0.0);
        Ok(SystemMetrics {
            cpu_usage,
            memory_usage,
            battery_level,
        })
    }

    fn memory_usage(&self) -> JarvisResult<f64> {
        unsafe {
            let mut status: MEMORYSTATUSEX = mem::zeroed();
            status.dwLength = mem::size_of::<MEMORYSTATUSEX>() as u32;
            if GlobalMemoryStatusEx(&mut status).is_ok() {
                let total = status.ullTotalPhys as f64;
                let avail = status.ullAvailPhys as f64;
                if total > 0.0 {
                    return Ok((1.0 - avail / total) * 100.0);
                }
                return Ok(0.0);
            }
        }
        Ok(0.0)
    }

    fn battery_level(&self) -> JarvisResult<f64> {
        unsafe {
            let mut status: SYSTEM_POWER_STATUS = mem::zeroed();
            if GetSystemPowerStatus(&mut status).is_ok() {
                let percent = status.BatteryLifePercent;
                if percent <= 100 {
                    return Ok(percent as f64);
                }
            }
        }
        Ok(0.0)
    }

    fn cpu_usage(&self) -> JarvisResult<f64> {
        unsafe {
            let mut idle = FILETIME::default();
            let mut kernel = FILETIME::default();
            let mut user = FILETIME::default();
            if GetSystemTimes(Some(&mut idle), Some(&mut kernel), Some(&mut user)).is_err() {
                return Ok(0.0);
            }
            let idle1 = filetime_to_u64(&idle);
            let total1 = filetime_to_u64(&kernel) + filetime_to_u64(&user);
            std::thread::sleep(std::time::Duration::from_millis(100));
            let mut idle2 = FILETIME::default();
            let mut kernel2 = FILETIME::default();
            let mut user2 = FILETIME::default();
            if GetSystemTimes(Some(&mut idle2), Some(&mut kernel2), Some(&mut user2)).is_err() {
                return Ok(0.0);
            }
            let idle2 = filetime_to_u64(&idle2);
            let total2 = filetime_to_u64(&kernel2) + filetime_to_u64(&user2);
            let idle_d = idle2.saturating_sub(idle1);
            let total_d = total2.saturating_sub(total1);
            if total_d > 0 {
                Ok((1.0 - (idle_d as f64 / total_d as f64)) * 100.0)
            } else {
                Ok(0.0)
            }
        }
    }
}

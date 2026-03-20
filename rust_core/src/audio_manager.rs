use crate::error::JarvisResult;

pub struct AudioManager;

impl AudioManager {
    pub fn new() -> Self {
        Self
    }

    pub fn set_master_volume(&self, _level: f32) -> JarvisResult<()> {
        // TODO: Реализация через WASAPI / IAudioEndpointVolume
        Ok(())
    }
}


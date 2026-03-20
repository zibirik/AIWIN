use crate::error::{JarvisError, JarvisResult};
use windows::Win32::UI::Input::KeyboardAndMouse::{
    SendInput, INPUT, INPUT_0, KEYBDINPUT, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE, INPUT_KEYBOARD,
    VIRTUAL_KEY,
};

#[derive(Clone)]
pub struct KeyboardController;

impl KeyboardController {
    pub fn new() -> Self {
        Self
    }

    pub fn send_text(&self, text: &str) -> JarvisResult<()> {
        unsafe {
            for ch in text.chars() {
                let code = ch as u16;
                let inputs = [
                    INPUT {
                        r#type: INPUT_KEYBOARD,
                        Anonymous: INPUT_0 {
                            ki: KEYBDINPUT {
                                wVk: VIRTUAL_KEY(0),
                                wScan: code,
                                dwFlags: KEYEVENTF_UNICODE,
                                time: 0,
                                dwExtraInfo: 0,
                            },
                        },
                    },
                    INPUT {
                        r#type: INPUT_KEYBOARD,
                        Anonymous: INPUT_0 {
                            ki: KEYBDINPUT {
                                wVk: VIRTUAL_KEY(0),
                                wScan: code,
                                dwFlags: KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                                time: 0,
                                dwExtraInfo: 0,
                            },
                        },
                    },
                ];
                let sent = SendInput(&inputs, std::mem::size_of::<INPUT>() as i32);
                if sent != 2 {
                    return Err(JarvisError::WinApi(format!("SendInput returned {}", sent)));
                }
            }
        }
        Ok(())
    }
}

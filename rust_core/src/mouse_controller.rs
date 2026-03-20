use crate::error::{JarvisError, JarvisResult};
use windows::Win32::UI::Input::KeyboardAndMouse::{
    SendInput, INPUT, INPUT_0, MOUSEINPUT, MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP,
    INPUT_MOUSE,
};
use windows::Win32::UI::WindowsAndMessaging::SetCursorPos;

#[derive(Clone)]
pub struct MouseController;

impl MouseController {
    pub fn new() -> Self {
        Self
    }

    pub fn move_to(&self, x: i32, y: i32) -> JarvisResult<()> {
        unsafe {
            SetCursorPos(x, y).map_err(|e| JarvisError::WinApi(format!("SetCursorPos: {e:?}")))?;
        }
        Ok(())
    }

    pub fn left_click(&self) -> JarvisResult<()> {
        unsafe {
            let inputs = [
                INPUT {
                    r#type: INPUT_MOUSE,
                    Anonymous: INPUT_0 {
                        mi: MOUSEINPUT {
                            dx: 0,
                            dy: 0,
                            mouseData: 0,
                            dwFlags: MOUSEEVENTF_LEFTDOWN,
                            time: 0,
                            dwExtraInfo: 0,
                        },
                    },
                },
                INPUT {
                    r#type: INPUT_MOUSE,
                    Anonymous: INPUT_0 {
                        mi: MOUSEINPUT {
                            dx: 0,
                            dy: 0,
                            mouseData: 0,
                            dwFlags: MOUSEEVENTF_LEFTUP,
                            time: 0,
                            dwExtraInfo: 0,
                        },
                    },
                },
            ];
            let sent = SendInput(&inputs, std::mem::size_of::<INPUT>() as i32);
            if sent != 2 {
                return Err(JarvisError::WinApi(format!("SendInput mouse returned {}", sent)));
            }
        }
        Ok(())
    }
}

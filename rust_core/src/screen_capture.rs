use crate::error::{JarvisError, JarvisResult};
use std::io::Cursor;
use windows::Win32::Graphics::Gdi::{
    BitBlt, CreateCompatibleBitmap, CreateCompatibleDC, DeleteDC, DeleteObject, GetDC, GetDIBits,
    GetDeviceCaps, ReleaseDC, SelectObject, BITMAPINFO, BITMAPINFOHEADER, DIB_RGB_COLORS,
    HORZRES, SRCCOPY, VERTRES,
};
use windows::Win32::UI::WindowsAndMessaging::GetDesktopWindow;

#[derive(Clone)]
pub struct ScreenCapture;

impl ScreenCapture {
    pub fn new() -> Self {
        Self
    }

    pub fn capture_fullscreen_png(&self) -> JarvisResult<Vec<u8>> {
        unsafe {
            let hwnd = GetDesktopWindow();
            let hdc_screen = GetDC(hwnd);
            if hdc_screen.is_invalid() {
                return Err(JarvisError::WinApi("GetDC failed".into()));
            }
            let (width, height) = {
                let w = GetDeviceCaps(hdc_screen, HORZRES);
                let h = GetDeviceCaps(hdc_screen, VERTRES);
                (w, h)
            };
            let hdc_mem = CreateCompatibleDC(hdc_screen);
            if hdc_mem.is_invalid() {
                ReleaseDC(hwnd, hdc_screen);
                return Err(JarvisError::WinApi("CreateCompatibleDC failed".into()));
            }
            let hbm = CreateCompatibleBitmap(hdc_screen, width, height);
            if hbm.is_invalid() {
                let _ = DeleteDC(hdc_mem);
                ReleaseDC(hwnd, hdc_screen);
                return Err(JarvisError::WinApi("CreateCompatibleBitmap failed".into()));
            }
            let _old = SelectObject(hdc_mem, hbm);
            let _ = BitBlt(
                hdc_mem,
                0,
                0,
                width,
                height,
                hdc_screen,
                0,
                0,
                SRCCOPY,
            );
            ReleaseDC(hwnd, hdc_screen);

            let mut bmi: BITMAPINFOHEADER = std::mem::zeroed();
            bmi.biSize = std::mem::size_of::<BITMAPINFOHEADER>() as u32;
            bmi.biWidth = width;
            bmi.biHeight = -(height as i32);
            bmi.biPlanes = 1;
            bmi.biBitCount = 32;
            bmi.biCompression = 0u32;
            let mut info = BITMAPINFO {
                bmiHeader: bmi,
                bmiColors: std::mem::zeroed(),
            };
            let row_bytes = (width as usize * 4 + 3) & !3;
            let size = row_bytes * height as usize;
            let mut pixels = vec![0u8; size];
            let lines = GetDIBits(
                hdc_mem,
                hbm,
                0,
                height as u32,
                Some(pixels.as_mut_ptr() as *mut _),
                &mut info,
                DIB_RGB_COLORS,
            );
            let _ = DeleteObject(hbm);
            let _ = DeleteDC(hdc_mem);

            if lines == 0 {
                return Err(JarvisError::WinApi("GetDIBits failed".into()));
            }

            let mut img = image::ImageBuffer::<image::Rgba<u8>, Vec<u8>>::new(width as u32, height as u32);
            for y in 0..height as u32 {
                for x in 0..width as u32 {
                    let i = (y as usize * row_bytes) + (x as usize * 4);
                    if i + 3 < pixels.len() {
                        let b = pixels[i];
                        let g = pixels[i + 1];
                        let r = pixels[i + 2];
                        let a = pixels[i + 3];
                        img.put_pixel(x, y, image::Rgba([r, g, b, a]));
                    }
                }
            }
            let mut out = Vec::new();
            let dyn_img = image::DynamicImage::ImageRgba8(img);
            dyn_img.write_to(&mut Cursor::new(&mut out), image::ImageFormat::Png)
                .map_err(|e| JarvisError::Internal(e.to_string()))?;
            Ok(out)
        }
    }
}

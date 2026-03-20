use thiserror::Error;

#[derive(Debug, Error)]
pub enum JarvisError {
    #[error("WinAPI error: {0}")]
    WinApi(String),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Invalid argument: {0}")]
    InvalidArgument(String),

    #[error("Internal error: {0}")]
    Internal(String),
}

pub type JarvisResult<T> = Result<T, JarvisError>;


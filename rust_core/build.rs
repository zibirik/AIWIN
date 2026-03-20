fn main() {
    let proto_file = "proto/system_control.proto";
    println!("cargo:rerun-if-changed={}", proto_file);

    // Используем встроенный protoc, чтобы не требовать установки в систему
    let protoc = protoc_bin_vendored::protoc_bin_path().expect("protoc not vendored");
    std::env::set_var("PROTOC", protoc);

    tonic_build::configure()
        .build_server(true)
        .build_client(true)
        .compile_protos(&[proto_file], &["proto"])
        .expect("failed to compile gRPC proto");
}


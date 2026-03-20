from jarvis_ai.server import create_app, run_app


def main() -> None:
    app = create_app()
    run_app(app)


if __name__ == "__main__":
    main()


import os

import uvicorn

from app.desktop_runtime import parse_desktop_args


def main(argv=None) -> None:
    args = parse_desktop_args(argv)
    os.environ.pop("SELLHELP_DATABASE_URL", None)
    environment = {
        "SELLHELP_DESKTOP_MODE": "1",
        "SELLHELP_DATA_DIR": str(args.data_dir),
    }
    if args.static_dir is not None:
        environment["SELLHELP_STATIC_DIR"] = str(args.static_dir)
    os.environ.update(environment)
    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, reload=False)


if __name__ == "__main__":
    main()

"""
KSdb CLI - Command-line interface for running KSdb server
"""
import argparse
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="KSdb - Vector Database Server")
    parser.add_argument("command", choices=["run", "version"], help="Command to execute")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--path", default=".ksdb", help="Path to store data")
    
    args = parser.parse_args()
    
    if args.command == "version":
        from ksdb import __version__
        print(f"KSdb version {__version__}")
        return
    
    if args.command == "run":
        # Set environment variables
        os.environ.setdefault("KSDB_DATA_PATH", args.path)
        
        # Import and run server
        import uvicorn
        from ksdb.server import app
        
        print(f"Starting KSdb server on {args.host}:{args.port}")
        print(f"Data directory: {args.path}")
        print(f"API docs: http://{args.host}:{args.port}/docs")
        
        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

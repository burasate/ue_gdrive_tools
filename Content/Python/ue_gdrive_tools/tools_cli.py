# -*- coding: utf-8 -*-
import os, time, json, sys, argparse, subprocess, hashlib
import zipfile36 as zipfile
class unreal_engine:
    @staticmethod
    def start(ue_editor_path, project_path):
        subprocess.Popen([ue_editor_path, project_path])

class hash_util:
    @staticmethod
    def get_md5_file_path(file_path):
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def get_md5_file_obj(file_obj):
        hash_md5 = hashlib.md5()
        for chunk in iter(lambda: file_obj.read(4096), b""):
            hash_md5.update(chunk)
        return hash_md5.hexdigest()

class zip_util:
    @staticmethod
    def zip_extract_file(zip_path, zip_src_path, project_dir):
        full_path = os.path.join(project_dir, zip_src_path)
        try:
            print(f"Extracting file: {zip_src_path}")
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extract(zip_src_path, project_dir)
        except:
            import traceback
            print(f"Unable to extract file: {zip_src_path}, Skip.")
            print(traceback.format_exc())
            time.sleep(2.5)

    @staticmethod
    def zip_files_with_hierarchy(files, zip_name, project_dir):
        assert isinstance(files, list)
        files = set(list(files))
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                arcname = os.path.relpath(file, project_dir)
                zf.write(file, arcname)
        print(f"Created zip file: {zip_name}")

class file_util:
    @staticmethod
    def remove_file(file_path):
        try:
            print(f"Romoving file: {file_path}")
            os.remove(file_path)
        except:
            import traceback
            print(f"Unable to remove file: {file_path}, Skip.")
            print(traceback.format_exc())

    @staticmethod
    def remove_empty_dirs(path):
        if not os.path.exists(path):
            return
        for root, dirs, files in os.walk(path, topdown=False):
            if not files and not dirs:
                try:
                    os.rmdir(root)
                    print(f"Removed empty directory: {root}")
                except OSError as e:
                    print(f"Could not remove {root}: {e}")

#---------------------------------------------------------------------------------
def main(argv=None):
    """Commandline interface."""
    parser = argparse.ArgumentParser(description="UE GDrive Tools")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommand to run")

    # Sync Re-Open Project
    extract_parser = subparsers.add_parser("restart", help="Restart and sync project")
    extract_parser.add_argument("-ueditor_path", type=str, required=True, help="Path to UnrealEditor.exe")
    extract_parser.add_argument("-file_path", type=str, required=True, help="Pull version log path")
    extract_parser.add_argument("-project_path", type=str, required=True, help="Pull version log path")

    args = parser.parse_args(argv)

    if args.command == "restart":
        print('\n=========\nRESTART PROJECT WITH SYNC\n=========\n')
        time.sleep(15)
        project_dir = os.path.dirname(args.project_path)
        with open(args.file_path) as f:
            rec = json.load(f)
            f.close()
        for zip_path, zip_src_path, mode in rec:
            if not zip_path:
                continue
            if mode == 0:
                file_path = os.path.join(project_dir, zip_src_path)
                file_util.remove_file(file_path)
            if mode == 1:
                zip_util.zip_extract_file(zip_path, zip_src_path, project_dir)
        file_util.remove_empty_dirs(os.path.join(project_dir, 'Content'))
        os.remove(args.file_path)
        print('\nStarting new editor window....')
        time.sleep(1)
        unreal_engine.start(args.ueditor_path, args.project_path)

#---------------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        main()
    except:
        import traceback
        print(str(traceback.format_exc()))
    finally:
        print('\n=========\nDONE\n=========\n')
        time.sleep(10)
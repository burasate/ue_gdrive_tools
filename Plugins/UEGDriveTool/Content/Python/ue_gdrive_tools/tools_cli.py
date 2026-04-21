# -*- coding: utf-8 -*-
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.request as ulib

import zipfile36 as zipfile


class unreal_engine:
    @staticmethod
    def _normalize_required_path(path_value, label):
        if path_value is None:
            raise ValueError(f"{label} is required.")

        path_value = str(path_value).strip()
        if not path_value:
            raise ValueError(f"{label} is required.")

        return os.path.abspath(os.path.expanduser(path_value))

    @staticmethod
    def start(ue_editor_path, project_path):
        ue_editor_path = unreal_engine._normalize_required_path(ue_editor_path, "Unreal editor path")
        project_path = unreal_engine._normalize_required_path(project_path, "Project path")

        if not os.path.isfile(ue_editor_path):
            raise FileNotFoundError(f"Unreal editor not found: {ue_editor_path}")
        if not os.path.exists(project_path):
            raise FileNotFoundError(f"Project path not found: {project_path}")

        try:
            return subprocess.Popen([ue_editor_path, project_path])
        except OSError as exc:
            raise RuntimeError(
                f"Unable to start Unreal editor '{ue_editor_path}' with project '{project_path}': {exc}"
            ) from exc


class hash_util:
    """Hash helpers.

    Note: the legacy get_md5_* names are compatibility aliases that still return
    SHA-256 digests to match existing project behavior.
    """

    COMPATIBILITY_DIGEST_NAME = "sha256"

    @staticmethod
    def _hash_file_obj(file_obj, algorithm="sha256"):
        hash_obj = hashlib.new(algorithm)
        for chunk in iter(lambda: file_obj.read(4096), b""):
            hash_obj.update(chunk)
        return hash_obj.hexdigest()

    @staticmethod
    def get_sha256_file_path(file_path):
        with open(file_path, "rb") as f:
            return hash_util._hash_file_obj(f, "sha256")

    @staticmethod
    def get_sha256_file_obj(file_obj):
        return hash_util._hash_file_obj(file_obj, "sha256")

    @staticmethod
    def get_md5_file_path(file_path):
        """Compatibility alias, returns a SHA-256 digest for legacy callers."""
        return hash_util.get_sha256_file_path(file_path)

    @staticmethod
    def get_md5_file_obj(file_obj):
        """Compatibility alias, returns a SHA-256 digest for legacy callers."""
        return hash_util.get_sha256_file_obj(file_obj)


class zip_util:
    @staticmethod
    def _normalize_zip_member_path(path_value):
        if path_value is None:
            raise ValueError("Zip member path is required.")

        normalized = str(path_value).strip().replace("\\", "/")
        if not normalized:
            raise ValueError("Zip member path is required.")
        if normalized.startswith("/"):
            raise ValueError(f"Absolute zip paths are not allowed: {path_value}")
        if len(normalized) >= 3 and normalized[1] == ":" and normalized[2] == "/":
            raise ValueError(f"Drive-qualified zip paths are not allowed: {path_value}")

        parts = []
        for part in normalized.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                raise ValueError(f"Unsafe zip path: {path_value}")
            parts.append(part)

        if not parts:
            raise ValueError(f"Unsafe zip path: {path_value}")

        return "/".join(parts)

    @staticmethod
    def _is_within_directory(path_value, directory):
        try:
            return os.path.commonpath([os.path.abspath(path_value), os.path.abspath(directory)]) == os.path.abspath(directory)
        except ValueError:
            return False

    @staticmethod
    def _resolve_project_path(project_dir, relative_path):
        project_dir = os.path.abspath(project_dir)
        target_path = os.path.abspath(os.path.join(project_dir, relative_path))
        if not zip_util._is_within_directory(target_path, project_dir):
            raise ValueError(f"Resolved path escapes project directory: {relative_path}")
        return target_path

    @staticmethod
    def _find_zip_member(zf, zip_src_path):
        normalized_src = zip_util._normalize_zip_member_path(zip_src_path)
        for member in zf.namelist():
            try:
                if zip_util._normalize_zip_member_path(member) == normalized_src:
                    return member
            except ValueError:
                continue
        raise KeyError(f"Zip member not found: {zip_src_path}")

    @staticmethod
    def zip_extract_file(zip_path, zip_src_path, project_dir):
        try:
            if not zip_path or not os.path.isfile(zip_path):
                raise FileNotFoundError(f"Zip file not found: {zip_path}")
            if not project_dir or not os.path.isdir(project_dir):
                raise NotADirectoryError(f"Project directory not found: {project_dir}")

            normalized_src = zip_util._normalize_zip_member_path(zip_src_path)
            target_path = zip_util._resolve_project_path(project_dir, normalized_src)

            print(f"Extracting file: {normalized_src}")
            with zipfile.ZipFile(zip_path, "r") as zf:
                member_name = zip_util._find_zip_member(zf, normalized_src)
                member_info = zf.getinfo(member_name)

                if member_info.filename.replace("\\", "/").endswith("/"):
                    os.makedirs(target_path, exist_ok=True)
                    return

                target_dir = os.path.dirname(target_path)
                if target_dir and not os.path.exists(target_dir):
                    os.makedirs(target_dir, exist_ok=True)

                with zf.open(member_info, "r") as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        except Exception as exc:
            import traceback
            print(f"Unable to extract file: {zip_src_path}, skipping.")
            print(traceback.format_exc())
            print(f"Extraction error ({exc.__class__.__name__}): {exc}")
            time.sleep(2.5)

    @staticmethod
    def zip_files_with_hierarchy(files, zip_name, project_dir):
        if not isinstance(files, list):
            raise TypeError("files must be a list")
        if not project_dir or not os.path.isdir(project_dir):
            raise NotADirectoryError(f"Project directory not found: {project_dir}")
        if not zip_name:
            raise ValueError("Zip output path is required.")

        unique_files = sorted(set(files))
        zip_dir = os.path.dirname(os.path.abspath(zip_name))
        if zip_dir and not os.path.exists(zip_dir):
            os.makedirs(zip_dir, exist_ok=True)

        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in unique_files:
                if not file_path:
                    print("Skipping empty file path.")
                    continue

                abs_file_path = os.path.abspath(file_path)
                if not os.path.exists(abs_file_path):
                    print(f"Skipping missing file: {file_path}")
                    continue
                if not os.path.isfile(abs_file_path):
                    print(f"Skipping non-file path: {file_path}")
                    continue
                if not zip_util._is_within_directory(abs_file_path, project_dir):
                    print(f"Skipping file outside project directory: {file_path}")
                    continue

                arcname = zip_util._normalize_zip_member_path(os.path.relpath(abs_file_path, project_dir))
                zf.write(abs_file_path, arcname)
        print(f"Created zip file: {zip_name}")


SUPPORT_MESSAGE_URL = os.environ.get("UE_GDRIVE_SUPPORT_URL")


def fetch_support_message(url=None, timeout=10):
    """Fetch a plain-text or JSON support payload from an explicit URL."""
    url = url or SUPPORT_MESSAGE_URL
    if not url:
        return None

    with ulib.urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def run_support_hook():
    """Load an optional support message from a configured service."""
    try:
        message = fetch_support_message()
    except Exception as exc:
        print(f"Support hook skipped: {exc}")
        return None

    if not message:
        print("Support hook skipped: no support URL configured.")
        return None

    message = message.strip()
    if not message:
        print("Support hook returned an empty message.")
        return None

    print("\n--------\nSupport hook message\n--------\n")
    print(message)
    return message


class file_util:
    @staticmethod
    def remove_file(file_path):
        if file_path is None:
            print("Skipping file removal: empty path.")
            return

        file_path = str(file_path).strip()
        if not file_path:
            print("Skipping file removal: empty path.")
            return

        abs_file_path = os.path.abspath(file_path)
        try:
            if not os.path.exists(abs_file_path):
                print(f"File already missing, skipping: {abs_file_path}")
                return
            if not os.path.isfile(abs_file_path):
                raise IsADirectoryError(f"Path is not a file: {abs_file_path}")

            print(f"Removing file: {abs_file_path}")
            os.remove(abs_file_path)
        except Exception as exc:
            import traceback
            print(f"Unable to remove file: {abs_file_path}, skipping.")
            print(traceback.format_exc())
            print(f"Removal error ({exc.__class__.__name__}): {exc}")

    @staticmethod
    def remove_empty_dirs(path):
        if path is None:
            return

        path = str(path).strip()
        if not path:
            return

        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return
        if not os.path.isdir(abs_path):
            print(f"Skipping empty directory cleanup, path is not a directory: {abs_path}")
            return

        for root, _, _ in os.walk(abs_path, topdown=False):
            try:
                if os.listdir(root):
                    continue
                os.rmdir(root)
                print(f"Removed empty directory: {root}")
            except OSError as exc:
                print(f"Could not remove empty directory {root}: {exc}")


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
        project_dir = os.path.dirname(os.path.abspath(args.project_path))
        with open(args.file_path) as f:
            rec = json.load(f)
        for zip_path, zip_src_path, mode in rec:
            if not zip_path:
                continue
            if mode == 0:
                file_path = os.path.join(project_dir, zip_src_path)
                file_util.remove_file(file_path)
            elif mode == 1:
                zip_util.zip_extract_file(zip_path, zip_src_path, project_dir)
        file_util.remove_empty_dirs(os.path.join(project_dir, 'Content'))
        file_util.remove_file(args.file_path)
        run_support_hook()
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

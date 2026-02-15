# -------------------------------
# gDrive Tools Starting up
# -------------------------------
import unreal, os

tool_path = os.path.join(os.path.dirname(__file__), 'gdrive_tools.py')
install_path = os.path.join(os.path.dirname(__file__), 'ue_gdrive_tools', 'install.py')
assert os.path.exists(install_path), 'install file deos not exists!'

editor_world = unreal.EditorLevelLibrary.get_editor_world()
if os.path.exists(tool_path):
	cmd = 'py ' + tool_path
	unreal.SystemLibrary.execute_console_command(editor_world, cmd)
else:
	cmd = 'py ' + install_path
	unreal.SystemLibrary.execute_console_command(editor_world, cmd)
# -------------------------------
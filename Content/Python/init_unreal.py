# dev environment
import ue_gdrive_tools.core as ugdrive
from importlib import reload
reload(ugdrive)
print(f'.\n=============\n{ugdrive.__file__}\n=============')


ugdrive.run()
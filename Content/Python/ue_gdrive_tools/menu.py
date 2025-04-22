# -*- coding: utf-8 -*-
'''
Thanks to original template
https://docs.google.com/document/d/18jIG5p6PRiO7qe8QgiFGQYnaRLKY-YyAYqZ0_hsOjFk/
'''
print(__file__)

import unreal
entry_owner = 'BRS_UE'
owning_menu_name = '.'.join(['LevelEditor', 'LevelEditorToolBar', 'User']) # Parent to
tool_menus = unreal.ToolMenus.get()

@unreal.uclass()
class SyncDrive_SubMenuEntry(unreal.ToolMenuEntryScript):
    def init_as_toolbar_button(self):
        self.data.menu = owning_menu_name
        self.data.advanced.entry_type = unreal.MultiBlockType.TOOL_BAR_COMBO_BUTTON
        self.data.icon = unreal.ScriptSlateIcon("EditorStyle", "Subversion.Branched")
        self.data.advanced.style_name_override = "CalloutToolbar"

def _clear_sub_menu():
    if not tool_menus.is_menu_registered(owning_menu_name):
        return
    toolbar_entry_name = "syncDriveToolbarEntry"
    submenu_name = f"{owning_menu_name}.{toolbar_entry_name}"

    # Refresh UI
    tool_menus.refresh_all_widgets()

def create():
    # Create Sync Drive button entry
    entry = SyncDrive_SubMenuEntry()
    entry.init_as_toolbar_button()
    entry.init_entry(
        entry_owner,
        owning_menu_name,
        "",
        "syncDriveToolbarEntry",
        "Sync Drive",
        "Drive Sync Tools and Utilities"
    )

    # Register submenu
    sub_menu = tool_menus.register_menu(
        owning_menu_name + ".syncDriveToolbarEntry",
        "",
        unreal.MultiBoxType.MENU,
        False
    )

    # Define Sync Drive menu entries
    menu_entries = [
        (
            "RunSyncFunction",
            "Sync",
            "Run the main sync function",
            "import unreal; print('Running main sync...')  # Replace with actual function",
            ("EditorStyle", "SourceControl.Actions.Refresh")
        ),
        None,
        (
            "SaveVersionFunction",
            "Save Version",
            "Run the main sync function",
            "import unreal; print('Running main sync...')  # Replace with actual function",
            ("EditorStyle", "Subversion.OpenForAdd")
        ),
        (
            "FetchVersionFunction",
            "Fetch Versions",
            "Run the main sync function",
            "import unreal; print('Running main sync...')  # Replace with actual function",
            ("EditorStyle", "SourceControl.Actions.Submit")
        ),
        None,
        (
            "UpdateScripting",
            "Check Update",
            "Update the tool",
            "import unreal; print('Updating scripting environment...')",
            None
        ),
        None,
        (
            "OpenDocumentation",
            "Open Documentation",
            "Open the documentation site",
            "unreal.SystemLibrary.launch_url(\"https://brsanim.notion.site/UE-GDrive-Tools-1dd721218164807abec1f65c49086311\")",
            ("EditorStyle", "GraphEditor.Documentation_16x")
        ),
    ]

    for idx, menu_entry in enumerate(menu_entries):
        if menu_entry is None:
            sub_entry = unreal.ToolMenuEntry(
                name=f'SepEntry_{idx}',
                type=unreal.MultiBlockType.SEPARATOR
            )
            sub_menu.add_menu_entry("", sub_entry)
        else:
            entry_name, display_name, description, command , icon = menu_entry

            sub_entry = unreal.ToolMenuEntryExtensions.init_menu_entry(
                entry_owner,  # Owner name
                entry_name,  # Entry name
                display_name,  # Display name
                description,  # Description
                unreal.ToolMenuStringCommandType.PYTHON,  # Command type
                "",  # Command string (not used here)
                command  # Python command to execute
            )
            if icon:
                sub_entry.set_icon(icon[0], icon[1])
            # Add
            sub_menu.add_menu_entry("", sub_entry)

    # Extend the toolbar menu and add the toolbar button
    toolbar = tool_menus.extend_menu(owning_menu_name)
    toolbar.add_menu_entry_object(entry)
    # Refresh the UI to show the new menu
    tool_menus.refresh_all_widgets()

if __name__ == '__main__':
    _clear_sub_menu()
    create()


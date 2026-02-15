# -*- coding: utf-8 -*-
'''
Thanks to original template
https://docs.google.com/document/d/18jIG5p6PRiO7qe8QgiFGQYnaRLKY-YyAYqZ0_hsOjFk/
'''
import unreal, sys

class UI:
    def __init__(self):
        self.entry_owner = 'BRS_UE'
        self.owning_menu_name = '.'.join(['LevelEditor', 'LevelEditorToolBar', 'User'])  # Parent to
        self.toolbar_entry_name = 'syncDriveToolbarEntry'
        self.submenu_name = f"{self.owning_menu_name}.{self.toolbar_entry_name}"
        self.get_tool_menus()

        # Define Sync Drive menu entries
        self.menu_entries = [
            (
                "RunSyncFunction",
                "Sync",
                "Run the main sync function",
                "ugdrive.sync()",
                ("EditorStyle", "SourceControl.Actions.Refresh")
            ),
            None,
            (
                "SaveVersionFunction",
                "Save Version",
                "Run the main sync function",
                "ugdrive.save()",
                ("EditorStyle", "Subversion.OpenForAdd")
            ),
            (
                "FetchVersionFunction",
                "Fetch Versions",
                "Run the main sync function",
                "ugdrive.load()",
                ("EditorStyle", "SourceControl.Actions.Submit")
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

    def get_tool_menus(self):
        self.tool_menus = unreal.ToolMenus.get()

    def _clear_sub_menu(self):
        self.get_tool_menus()
        sub_menu = self.tool_menus.find_menu(self.submenu_name)
        if not sub_menu:
            return

        # Refresh UI
        self.tool_menus.refresh_all_widgets()

    def _create_tool_menus(self):
        # Create Sync Drive button entry
        entry = SyncDrive_SubMenuEntry()
        entry.init_as_toolbar_button()
        entry.init_entry(
            self.entry_owner,
            self.owning_menu_name,
            "",
            self.toolbar_entry_name,
            "Sync Drive",
            "Drive Sync Tools and Utilities"
        )

        # Register submenu
        sub_menu = self.tool_menus.register_menu(
            self.submenu_name,
            "",
            unreal.MultiBoxType.MENU,
            False
        )

        for idx, menu_entry in enumerate(self.menu_entries):
            if menu_entry is None:
                sub_entry = unreal.ToolMenuEntry(
                    name=f'SepEntry_{idx}',
                    type=unreal.MultiBlockType.SEPARATOR
                )
                sub_menu.add_menu_entry("", sub_entry)
            else:
                entry_name, display_name, description, command , icon = menu_entry

                sub_entry = unreal.ToolMenuEntryExtensions.init_menu_entry(
                    self.entry_owner,  # Owner name
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
        toolbar = self.tool_menus.extend_menu(self.owning_menu_name)
        toolbar.add_menu_entry_object(entry)
        # Refresh the UI to show the new menu
        self.tool_menus.refresh_all_widgets()

@unreal.uclass()
class SyncDrive_SubMenuEntry(unreal.ToolMenuEntryScript):
    def init_as_toolbar_button(self):
        global UI
        self.data.menu = UI().owning_menu_name
        self.data.advanced.entry_type = unreal.MultiBlockType.TOOL_BAR_COMBO_BUTTON
        self.data.icon = unreal.ScriptSlateIcon("EditorStyle", "Subversion.Branched")
        self.data.advanced.style_name_override = "CalloutToolbar"

if __name__ == '__main__':
    um = ui_menu()
    um._clear_sub_menu()
    um._create_tool_menus()


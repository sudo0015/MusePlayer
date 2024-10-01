from qfluentwidgets import qconfig, QConfig, ConfigItem, OptionsConfigItem, BoolValidator, OptionsValidator, \
    FolderValidator


class Config(QConfig):
    musicFolder = ConfigItem(
        "Folders", "Music", "music", FolderValidator())
    enableAcrylicBackground = ConfigItem(
        "MainWindow", "EnableAcrylicBackground", False, BoolValidator())
    dpiScale = OptionsConfigItem(
        "MainWindow", "DpiScale", "Auto", OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True)
    checkUpdateAtStartUp = ConfigItem(
        "Update", "CheckUpdateAtStartUp", True, BoolValidator())


HELP_URL = ""
cfg = Config()
qconfig.load('config/config.json', cfg)

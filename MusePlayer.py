import os
import sys
import mutagen
import subprocess
from typing import Union
from config import cfg, HELP_URL
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation, QObject, QUrl
from PySide6.QtGui import QIcon, QShortcut, QKeySequence, QColor, QPainter
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QStackedWidget, QVBoxLayout, QLabel, QFileDialog, \
    QButtonGroup, QPushButton, QGraphicsOpacityEffect
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from qframelesswindow import FramelessWindow, StandardTitleBar
from qfluentwidgets import SettingCardGroup, SwitchSettingCard, PushSettingCard, HyperlinkCard, ScrollArea, \
    ExpandSettingCard, ExpandLayout, Theme, InfoBar, setTheme, setThemeColor, isDarkTheme, SegmentedWidget, \
    ColorDialog, ExpandGroupSettingCard, RadioButton, qconfig, ColorConfigItem, FluentIconBase, \
    TransparentDropDownPushButton, RoundMenu, CommandBar, Action, setFont, ImageLabel, FluentStyleSheet, \
    TransparentToolButton, ToolTipFilter, Slider, CaptionLabel, Flyout, FlyoutViewBase
from qfluentwidgets.components.widgets.flyout import SlideLeftFlyoutAnimationManager
from qfluentwidgets import FluentIcon as FIF


class MediaPlayerBase(QObject):
    mediaStatusChanged = Signal(QMediaPlayer.MediaStatus)
    playbackRateChanged = Signal(float)
    positionChanged = Signal(int)
    durationChanged = Signal(int)
    sourceChanged = Signal(QUrl)
    volumeChanged = Signal(int)
    mutedChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def isPlaying(self):
        raise NotImplementedError

    def mediaStatus(self) -> QMediaPlayer.MediaStatus:
        raise NotImplementedError

    def playbackState(self) -> QMediaPlayer.PlaybackState:
        raise NotImplementedError

    def duration(self):
        raise NotImplementedError

    def position(self):
        raise NotImplementedError

    def volume(self):
        raise NotImplementedError

    def source(self) -> QUrl:
        raise NotImplementedError

    def pause(self):
        raise NotImplementedError

    def play(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def playbackRate(self) -> float:
        raise NotImplementedError

    def setPosition(self, position: int):
        raise NotImplementedError

    def setSource(self, media: QUrl):
        raise NotImplementedError

    def setPlaybackRate(self, rate: float):
        raise NotImplementedError

    def setVolume(self, volume: int):
        raise NotImplementedError

    def setMuted(self, isMuted: bool):
        raise NotImplementedError

    def videoOutput(self) -> QObject:
        raise NotImplementedError

    def setVideoOutput(self, output: QObject) -> None:
        raise NotImplementedError


class MediaPlayer(QMediaPlayer):
    sourceChanged = Signal(QUrl)
    mutedChanged = Signal(bool)
    volumeChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._audioOutput = QAudioOutput(parent)
        self.setAudioOutput(self._audioOutput)

    def isPlaying(self):
        return self.playbackState() == QMediaPlayer.PlayingState

    def volume(self):
        return int(self.audioOutput().volume() * 100)

    def setVolume(self, volume: int):
        if volume == self.volume():
            return
        self.audioOutput().setVolume(volume / 100)
        self.volumeChanged.emit(volume)

    def setMuted(self, isMuted: bool):
        if isMuted == self.audioOutput().isMuted():
            return
        self.audioOutput().setMuted(isMuted)
        self.mutedChanged.emit(isMuted)


class MediaPlayBarButton(TransparentToolButton):
    def _postInit(self):
        super()._postInit()
        self.installEventFilter(ToolTipFilter(self, 1000))
        self.setFixedSize(30, 30)
        self.setIconSize(QSize(16, 16))


class PlayButton(MediaPlayBarButton):
    def _postInit(self):
        super()._postInit()
        self.setIconSize(QSize(14, 14))
        self.setPlay(False)

    def setPlay(self, isPlay: bool):
        if isPlay:
            self.setIcon(FIF.PAUSE_BOLD)
            self.setToolTip(self.tr('暂停'))
        else:
            self.setIcon(FIF.PLAY_SOLID)
            self.setToolTip(self.tr('播放'))


class VolumeView(FlyoutViewBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.muteButton = MediaPlayBarButton(FIF.VOLUME, self)
        self.volumeSlider = Slider(Qt.Horizontal, self)
        self.volumeLabel = CaptionLabel('30', self)
        self.volumeSlider.setRange(0, 100)
        self.volumeSlider.setFixedWidth(208)
        self.setFixedSize(295, 64)
        h = self.height()
        self.muteButton.move(10, h // 2 - self.muteButton.height() // 2)
        self.volumeSlider.move(45, 21)

    def setMuted(self, isMute: bool):
        if isMute:
            self.muteButton.setIcon(FIF.MUTE)
            self.muteButton.setToolTip(self.tr('取消静音'))
        else:
            self.muteButton.setIcon(FIF.VOLUME)
            self.muteButton.setToolTip(self.tr('静音'))

    def setVolume(self, volume: int):
        self.volumeSlider.setValue(volume)
        self.volumeLabel.setNum(volume)
        self.volumeLabel.adjustSize()
        tr = self.volumeLabel.fontMetrics().boundingRect(str(volume))
        self.volumeLabel.move(self.width() - 20 - tr.width(), self.height() // 2 - tr.height() // 2)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)
        if isDarkTheme():
            painter.setBrush(QColor(46, 46, 46))
            painter.setPen(QColor(0, 0, 0, 20))
        else:
            painter.setBrush(QColor(248, 248, 248))
            painter.setPen(QColor(0, 0, 0, 10))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)


class VolumeButton(MediaPlayBarButton):
    volumeChanged = Signal(int)
    mutedChanged = Signal(bool)

    def _postInit(self):
        super()._postInit()
        self.volumeView = VolumeView(self)
        self.volumeFlyout = Flyout(self.volumeView, self.window(), False)
        self.setMuted(False)
        self.volumeFlyout.hide()
        self.volumeView.muteButton.clicked.connect(lambda: self.mutedChanged.emit(not self.isMuted))
        self.volumeView.volumeSlider.valueChanged.connect(self.volumeChanged)
        self.clicked.connect(self._showVolumeFlyout)

    def setMuted(self, isMute: bool):
        self.isMuted = isMute
        self.volumeView.setMuted(isMute)
        if isMute:
            self.setIcon(FIF.MUTE)
        else:
            self.setIcon(FIF.VOLUME)

    def setVolume(self, volume: int):
        self.volumeView.setVolume(volume)

    def _showVolumeFlyout(self):
        if self.volumeFlyout.isVisible():
            return
        pos = SlideLeftFlyoutAnimationManager(self.volumeFlyout).position(self)
        self.volumeFlyout.exec(pos)


class MediaPlayBarBase(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.player = None
        self.isLoop = False

        self.playButton = PlayButton(self)
        self.volumeButton = VolumeButton(self)
        self.progressSlider = Slider(Qt.Horizontal, self)
        self.opacityEffect = QGraphicsOpacityEffect(self)
        self.opacityAni = QPropertyAnimation(self.opacityEffect, b'opacity')
        self.opacityEffect.setOpacity(1)
        self.opacityAni.setDuration(250)
        self.setGraphicsEffect(self.opacityEffect)
        FluentStyleSheet.MEDIA_PLAYER.apply(self)

    def setMediaPlayer(self, player: MediaPlayerBase):
        self.player = player
        self.player.durationChanged.connect(self.progressSlider.setMaximum)
        self.player.positionChanged.connect(self._onPositionChanged)
        self.player.mediaStatusChanged.connect(self._onMediaStatusChanged)
        self.player.volumeChanged.connect(self.volumeButton.setVolume)
        self.player.mutedChanged.connect(self.volumeButton.setMuted)
        self.progressSlider.sliderMoved.connect(self.player.setPosition)
        self.progressSlider.clicked.connect(self.player.setPosition)
        self.playButton.clicked.connect(self.togglePlayState)
        self.volumeButton.volumeChanged.connect(self.player.setVolume)
        self.volumeButton.mutedChanged.connect(self.player.setMuted)
        self.player.setVolume(30)

    def fadeIn(self):
        self.opacityAni.setStartValue(self.opacityEffect.opacity())
        self.opacityAni.setEndValue(1)
        self.opacityAni.start()

    def fadeOut(self):
        self.opacityAni.setStartValue(self.opacityEffect.opacity())
        self.opacityAni.setEndValue(0)
        self.opacityAni.start()

    def play(self):
        self.player.play()
        self.playButton.setPlay(True)

    def pause(self):
        self.player.pause()
        self.playButton.setPlay(False)

    def stop(self):
        self.player.stop()

    def setLoop(self, arg: bool):
        if arg:
            self.isLoop = True
        else:
            self.isLoop = False

    def setVolume(self, volume: int):
        self.player.setVolume(volume)

    def setPosition(self, position: int):
        self.player.setPosition(position)

    def _onPositionChanged(self, position: int):
        self.progressSlider.setValue(position)

    def _onMediaStatusChanged(self, status):
        self.playButton.setPlay(self.player.isPlaying())

    def togglePlayState(self):
        if self.player.isPlaying():
            self.player.pause()
        else:
            self.player.play()
        self.playButton.setPlay(self.player.isPlaying())

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)
        if isDarkTheme():
            painter.setBrush(QColor(46, 46, 46))
            painter.setPen(QColor(0, 0, 0, 20))
        else:
            painter.setBrush(QColor(248, 248, 248))
            painter.setPen(QColor(0, 0, 0, 10))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)


class StandardMediaPlayBar(MediaPlayBarBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vBoxLayout = QVBoxLayout(self)
        self.timeLayout = QHBoxLayout()
        self.buttonLayout = QHBoxLayout()
        self.leftButtonContainer = QWidget()
        self.centerButtonContainer = QWidget()
        self.rightButtonContainer = QWidget()
        self.leftButtonLayout = QHBoxLayout(self.leftButtonContainer)
        self.centerButtonLayout = QHBoxLayout(self.centerButtonContainer)
        self.rightButtonLayout = QHBoxLayout(self.rightButtonContainer)
        self.skipBackButton = MediaPlayBarButton(FIF.SKIP_BACK, self)
        self.skipForwardButton = MediaPlayBarButton(FIF.SKIP_FORWARD, self)
        self.currentTimeLabel = CaptionLabel('0:00:00', self)
        self.remainTimeLabel = CaptionLabel('0:00:00', self)
        self.__initWidgets()

    def __initWidgets(self):
        self.setFixedHeight(102)
        self.vBoxLayout.setSpacing(6)
        self.vBoxLayout.setContentsMargins(5, 9, 5, 9)
        self.vBoxLayout.addWidget(self.progressSlider, 1, Qt.AlignTop)
        self.vBoxLayout.addLayout(self.timeLayout)
        self.timeLayout.setContentsMargins(10, 0, 10, 0)
        self.timeLayout.addWidget(self.currentTimeLabel, 0, Qt.AlignLeft)
        self.timeLayout.addWidget(self.remainTimeLabel, 0, Qt.AlignRight)
        self.vBoxLayout.addStretch(1)
        self.vBoxLayout.addLayout(self.buttonLayout, 1)
        self.buttonLayout.setContentsMargins(0, 0, 0, 0)
        self.leftButtonLayout.setContentsMargins(4, 0, 0, 0)
        self.centerButtonLayout.setContentsMargins(0, 0, 0, 0)
        self.rightButtonLayout.setContentsMargins(0, 0, 4, 0)
        self.rightButtonLayout.addWidget(self.volumeButton, 0, Qt.AlignRight)
        self.centerButtonLayout.addWidget(self.skipBackButton)
        self.centerButtonLayout.addWidget(self.playButton)
        self.centerButtonLayout.addWidget(self.skipForwardButton)
        self.buttonLayout.addWidget(self.leftButtonContainer, 0, Qt.AlignLeft)
        self.buttonLayout.addWidget(self.centerButtonContainer, 0, Qt.AlignHCenter)
        self.buttonLayout.addWidget(self.rightButtonContainer, 0, Qt.AlignRight)
        self.setMediaPlayer(MediaPlayer(self))
        self.skipBackButton.clicked.connect(lambda: self.skipBack(10000))
        self.skipForwardButton.clicked.connect(lambda: self.skipForward(30000))

    def skipBack(self, ms: int):
        self.player.setPosition(self.player.position() - ms)

    def skipForward(self, ms: int):
        self.player.setPosition(self.player.position() + ms)

    def _onPositionChanged(self, position: int):
        super()._onPositionChanged(position)
        self.currentTimeLabel.setText(self._formatTime(position))
        self.remainTimeLabel.setText(self._formatTime(self.player.duration() - position))
        if self._formatTime(self.player.duration() - position) == "0:00:00" and self.isLoop:
            self.player.stop()
            self.player.play()

    def _formatTime(self, time: int):
        time = int(time / 1000)
        s = time % 60
        m = int(time / 60)
        h = int(time / 3600)
        return f'{h}:{m:02}:{s:02}'


class PlayInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.isLoop = False
        self.vBoxLayout = QVBoxLayout(self)
        self.hBoxLayout = QHBoxLayout(self)
        self.commandBar = CommandBar(self)
        self.addButtonAdd(FIF.ADD, '打开')
        self.hBoxLayout.addWidget(self.commandBar, 0)
        self.commandBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.commandBar.addSeparator()
        self.commandBar.addAction(Action(FIF.SYNC, '循环', triggered=self.onLoop, checkable=True))
        self.commandBar.addWidget(self.createDropDownButtonSpeed())
        self.commandBar.addSeparator()
        self.addButtonInfo(FIF.INFO, '属性')
        self.addButtonShare(FIF.SHARE, '分享')
        self.standardPlayBar = StandardMediaPlayBar(self)
        self.standardPlayBar.setLoop(True) if self.isLoop else self.standardPlayBar.setLoop(False)
        self.imgLabel = ImageLabel(self)
        if isDarkTheme():
            self.imgLabel.setImage('./resource/img/AlbumDark.png')
        else:
            self.imgLabel.setImage('./resource/img/AlbumLight.png')
        self.imgLabel.setBorderRadius(10, 10, 10, 10)
        self.imgLabel.setFixedSize(100, 100)
        self.hoLayout = QHBoxLayout(self)
        self.hoLayout.setContentsMargins(0, 0, 0, 0)
        self.hoLayout.addWidget(self.imgLabel)
        self.hoLayout.addWidget(self.standardPlayBar)
        self.standardPlayBar.volumeButton.setVolume(100)
        self.vBoxLayout.addWidget(self.commandBar)
        self.vBoxLayout.addStretch()
        self.vBoxLayout.addLayout(self.hoLayout)
        self.standardPlayBar.volumeButton.setVolume(100)
        self.setQss()
        cfg.themeChanged.connect(self.setQss)

    def addButtonAdd(self, icon, text):
        action = Action(icon, text, self)
        action.triggered.connect(lambda: self.filePick())
        self.commandBar.addAction(action)

    def addButtonInfo(self, icon, text):
        action = Action(icon, text, self)
        action.triggered.connect(lambda: print(text))
        self.commandBar.addAction(action)

    def addButtonShare(self, icon, text):
        action = Action(icon, text, self)
        action.triggered.connect(lambda: self.OpenWith())
        self.commandBar.addAction(action)

    def createDropDownButtonSpeed(self):
        button = TransparentDropDownPushButton('倍速', self, FIF.SPEED_HIGH)
        button.setFixedHeight(34)
        setFont(button, 12)
        menu = RoundMenu(parent=self)
        menu.addActions([Action('1 ⨯'), ])
        button.setMenu(menu)
        return button

    def setQss(self):
        theme = 'dark' if isDarkTheme() else 'light'
        with open(f'resource/qss/{theme}/main.qss', encoding='utf-8') as f:
            self.setStyleSheet(f.read())

    def onLoop(self, isChecked):
        if isChecked:
            self.isLoop = True
        else:
            self.isLoop = False
        self.standardPlayBar.setLoop(True) if self.isLoop else self.standardPlayBar.setLoop(False)

    def OpenWith(self):
        args = ["C:\\Windows\\System32\\OpenWith.exe", self.FileDirectory.replace("/", "\\")]
        subprocess.run(args, shell=True)

    def DetectPic(self):
        try:
            x = self.audio.pictures
            if x:
                return True
        except Exception:
            pass
        if 'covr' in self.audio or 'APIC:' in self.audio:
            return True
        return False

    def filePick(self):
        self.FileDirectory = QFileDialog.getOpenFileName(self, "打开文件", cfg.musicFolder.value,
                                                         "音频文件 (*.mp3 *.acc *.wma *.wav *.ogg *.m4a *.ape *.flac *.cue);;所有文件 (*.*)")[
            0]
        if self.FileDirectory:
            self.standardPlayBar.deleteLater()
            self.standardPlayBar = StandardMediaPlayBar(self)
            self.standardPlayBar.volumeButton.setVolume(100)
            self.standardPlayBar.setLoop(True) if self.isLoop else self.standardPlayBar.setLoop(False)
            self.hoLayout.addWidget(self.standardPlayBar)
            self.standardPlayBar.player.setSource(self.FileDirectory)
            self.standardPlayBar.play()
            self.audio = mutagen.File(self.FileDirectory)
            if self.DetectPic():
                try:
                    if self.audio.pictures:
                        self.cover = self.audio.pictures
                except Exception:
                    pass
                if 'covr' in self.audio:
                    self.cover = self.audio.tags['covr'].data
                if 'APIC:' in self.audio:
                    self.cover = self.audio.tags['APIC:'].data
                # img = open('./resource/img/cover.jpg', 'wb')
                # img.write(self.cover)
                # img.close()
                with open('./resource/img/cover.jpg', 'wb') as img:
                    img.write(self.cover)
                self.imgLabel.setImage('./resource/img/cover.jpg')
                self.imgLabel.setBorderRadius(10, 10, 10, 10)
                self.imgLabel.setFixedSize(100, 100)
            else:
                if isDarkTheme():
                    self.imgLabel.setImage('./resource/img/AlbumDark.png')
                else:
                    self.imgLabel.setImage('./resource/img/AlbumLight.png')
                self.imgLabel.setBorderRadius(10, 10, 10, 10)
                self.imgLabel.setFixedSize(100, 100)


class CustomColorSettingCard(ExpandGroupSettingCard):
    colorChanged = Signal(QColor)

    def __init__(self, configItem: ColorConfigItem, icon: Union[str, QIcon, FluentIconBase], title: str, content=None,
                 parent=None, enableAlpha=False):
        super().__init__(icon, title, content, parent=parent)
        self.enableAlpha = enableAlpha
        self.configItem = configItem
        self.defaultColor = QColor(configItem.defaultValue)
        self.customColor = QColor(qconfig.get(configItem))
        self.choiceLabel = QLabel(self)
        self.radioWidget = QWidget(self.view)
        self.radioLayout = QVBoxLayout(self.radioWidget)
        self.defaultRadioButton = RadioButton(self.tr('默认'), self.radioWidget)
        self.customRadioButton = RadioButton(self.tr('自定义'), self.radioWidget)
        self.buttonGroup = QButtonGroup(self)
        self.customColorWidget = QWidget(self.view)
        self.customColorLayout = QHBoxLayout(self.customColorWidget)
        self.customLabel = QLabel(self.tr('自定义'), self.customColorWidget)
        self.chooseColorButton = QPushButton(self.tr('选择颜色'), self.customColorWidget)
        self.__initWidget()

    def __initWidget(self):
        self.__initLayout()
        if self.defaultColor != self.customColor:
            self.customRadioButton.setChecked(True)
            self.chooseColorButton.setEnabled(True)
        else:
            self.defaultRadioButton.setChecked(True)
            self.chooseColorButton.setEnabled(False)
        self.choiceLabel.setText(self.buttonGroup.checkedButton().text())
        self.choiceLabel.adjustSize()
        self.chooseColorButton.setObjectName('chooseColorButton')
        self.buttonGroup.buttonClicked.connect(self.__onRadioButtonClicked)
        self.chooseColorButton.clicked.connect(self.__showColorDialog)

    def __initLayout(self):
        self.addWidget(self.choiceLabel)

        self.radioLayout.setSpacing(19)
        self.radioLayout.setAlignment(Qt.AlignTop)
        self.radioLayout.setContentsMargins(48, 18, 0, 18)
        self.buttonGroup.addButton(self.customRadioButton)
        self.buttonGroup.addButton(self.defaultRadioButton)
        self.radioLayout.addWidget(self.customRadioButton)
        self.radioLayout.addWidget(self.defaultRadioButton)
        self.radioLayout.setSizeConstraint(QVBoxLayout.SetMinimumSize)

        self.customColorLayout.setContentsMargins(48, 18, 44, 18)
        self.customColorLayout.addWidget(self.customLabel, 0, Qt.AlignLeft)
        self.customColorLayout.addWidget(self.chooseColorButton, 0, Qt.AlignRight)
        self.customColorLayout.setSizeConstraint(QHBoxLayout.SetMinimumSize)

        self.viewLayout.setSpacing(0)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.addGroupWidget(self.radioWidget)
        self.addGroupWidget(self.customColorWidget)

    def __onRadioButtonClicked(self, button: RadioButton):
        if button.text() == self.choiceLabel.text():
            return
        self.choiceLabel.setText(button.text())
        self.choiceLabel.adjustSize()
        if button is self.defaultRadioButton:
            self.chooseColorButton.setDisabled(True)
            qconfig.set(self.configItem, self.defaultColor)
            if self.defaultColor != self.customColor:
                self.colorChanged.emit(self.defaultColor)
        else:
            self.chooseColorButton.setDisabled(False)
            qconfig.set(self.configItem, self.customColor)
            if self.defaultColor != self.customColor:
                self.colorChanged.emit(self.customColor)

    def __showColorDialog(self):
        w = ColorDialog(qconfig.get(self.configItem), self.tr('选择颜色'), self.window(), self.enableAlpha)
        w.colorChanged.connect(self.__onCustomColorChanged)
        w.exec()

    def __onCustomColorChanged(self, color):
        qconfig.set(self.configItem, color)
        self.customColor = QColor(color)
        self.colorChanged.emit(color)


class SettingInterface(ScrollArea):
    acrylicEnableChanged = Signal(bool)
    musicFolderChanged = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)
        self.personalGroup = SettingCardGroup(self.tr('设置'), self.scrollWidget)
        self.enableAcrylicCard = SwitchSettingCard(
            FIF.TRANSPARENT,
            self.tr("透明效果"),
            self.tr("窗口和表面显示半透明"),
            configItem=cfg.enableAcrylicBackground,
            parent=self.personalGroup)
        self.themeColorCard = CustomColorSettingCard(
            cfg.themeColor,
            FIF.PALETTE,
            self.tr('主题色'),
            self.tr('更改应用主题色'),
            self.personalGroup)
        self.musicFolderCard = PushSettingCard(
            self.tr('选择文件夹'),
            FIF.MUSIC_FOLDER,
            self.tr("音乐文件夹"),
            cfg.get(cfg.musicFolder),
            self.personalGroup)
        self.aboutGroup = SettingCardGroup(self.tr('关于'), self.scrollWidget)
        self.helpCard = HyperlinkCard(
            HELP_URL,
            self.tr('打开帮助'),
            FIF.HELP,
            self.tr('帮助'),
            self.tr('获取提示与帮助'),
            self.aboutGroup)
        self.aboutCard = ExpandSettingCard(
            FIF.INFO,
            self.tr('关于'),
            self.tr('MusePlayer'),
            self.aboutGroup)
        self.aboutCard.viewLayout.addWidget(
            QLabel("MusePlayer (v1.1.0)\nCopyright © 2024 BUG STUDIO. All rights reserved."))
        self.__initWidget()

    def __initWidget(self):
        self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 20, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.__setQss()
        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        self.personalGroup.addSettingCard(self.enableAcrylicCard)
        self.personalGroup.addSettingCard(self.themeColorCard)
        self.personalGroup.addSettingCard(self.musicFolderCard)
        self.aboutGroup.addSettingCard(self.helpCard)
        self.aboutGroup.addSettingCard(self.aboutCard)
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(60, 10, 60, 0)
        self.expandLayout.addWidget(self.personalGroup)
        self.expandLayout.addWidget(self.aboutGroup)

    def __setQss(self):
        self.scrollWidget.setObjectName('scrollWidget')
        theme = 'dark' if isDarkTheme() else 'light'
        with open(f'resource/qss/{theme}/setting_interface.qss', encoding='utf-8') as f:
            self.setStyleSheet(f.read())

    def __showRestartTooltip(self):
        InfoBar.warning(
            '',
            self.tr('重启后生效'),
            parent=self.window())

    def __onMusicFolderCardClicked(self):
        folder = QFileDialog.getExistingDirectory(self, self.tr("选择文件夹"), "./")
        if not folder or cfg.get(cfg.musicFolder) == folder:
            return
        cfg.set(cfg.musicFolder, folder)
        self.musicFolderCard.setContent(folder)

    def __onThemeChanged(self, theme: Theme):
        setTheme(theme)
        self.__setQss()

    def __connectSignalToSlot(self):
        cfg.appRestartSig.connect(self.__showRestartTooltip)
        cfg.themeChanged.connect(self.__onThemeChanged)
        self.musicFolderCard.clicked.connect(self.__onMusicFolderCardClicked)
        self.enableAcrylicCard.checkedChanged.connect(self.acrylicEnableChanged)
        self.themeColorCard.colorChanged.connect(setThemeColor)


class Window(FramelessWindow):
    def __init__(self):
        super().__init__()
        self.setTitleBar(StandardTitleBar(self))
        self.vBoxLayout = QVBoxLayout(self)
        self.playInterface = PlayInterface(self)
        self.settingInterface = SettingInterface(self)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.pivot = SegmentedWidget(self)
        self.stackedWidget = QStackedWidget(self)
        self.veBoxLayout = QVBoxLayout(self)
        self.listInterface = QLabel('        Developing...(=￣ω￣=)', self)
        self.addSubInterface(self.playInterface, 'playInterface', '播放')
        self.addSubInterface(self.listInterface, 'listInterface', '列表')
        self.addSubInterface(self.settingInterface, 'settingInterface', '设置')
        self.veBoxLayout.addWidget(self.pivot)
        self.veBoxLayout.addWidget(self.stackedWidget)
        self.veBoxLayout.setContentsMargins(30, 10, 30, 30)
        self.stackedWidget.setCurrentWidget(self.playInterface)
        self.pivot.setCurrentItem(self.playInterface.objectName())
        self.pivot.currentItemChanged.connect(lambda k: self.stackedWidget.setCurrentWidget(self.findChild(QWidget, k)))
        self.PivotLayout = QHBoxLayout(self)
        self.PivotLayout.addWidget(self.pivot)
        self.PivotLayout.setContentsMargins(100, 0, 100, 0)
        self.vBoxLayout.addWidget(self.titleBar)
        self.vBoxLayout.addLayout(self.PivotLayout)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.vBoxLayout.setAlignment(Qt.AlignCenter)
        self.setWindowIcon(QIcon("./resource/img/icon.png"))
        self.setWindowTitle("MusePlayer")
        self.resize(730, 260)
        desktop = QApplication.screens()[0].size()
        self.move(desktop.width() // 2 - self.width() // 2, desktop.height() // 2 - self.height() // 2)
        self.titleBar.raise_()
        self.setQss()
        cfg.themeChanged.connect(self.setQss)
        self.KeyOpen()
        self.KeyPlayAndPause()
        self.KeySetting()
        self.KeyPage1()
        self.KeyPage2()
        self.KeyPage3()

    def KeyOpen(self):
        shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        shortcut.activated.connect(lambda: self.playInterface.filePick())

    def KeyPlayAndPause(self):
        shortcut = QShortcut(QKeySequence("Space"), self)
        shortcut.activated.connect(lambda: self.playInterface.standardPlayBar.togglePlayState())

    def KeySetting(self):
        shortcut = QShortcut(QKeySequence("Ctrl+,"), self)
        shortcut.activated.connect(lambda: self.pivot.setCurrentItem(self.settingInterface.objectName()))

    def KeyPage1(self):
        shortcut = QShortcut(QKeySequence("Ctrl+1"), self)
        shortcut.activated.connect(lambda: self.pivot.setCurrentItem(self.playInterface.objectName()))

    def KeyPage2(self):
        shortcut = QShortcut(QKeySequence("Ctrl+2"), self)
        shortcut.activated.connect(lambda: self.pivot.setCurrentItem(self.listInterface.objectName()))

    def KeyPage3(self):
        shortcut = QShortcut(QKeySequence("Ctrl+3"), self)
        shortcut.activated.connect(lambda: self.pivot.setCurrentItem(self.settingInterface.objectName()))

    def addSubInterface(self, widget: QLabel, objectName, text):
        widget.setObjectName(objectName)
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(routeKey=objectName, text=text)

    def setQss(self):
        theme = 'dark' if isDarkTheme() else 'light'
        with open(f'resource/qss/{theme}/main.qss', encoding='utf-8') as f:
            self.setStyleSheet(f.read())


if __name__ == '__main__':
    if cfg.get(cfg.dpiScale) == "Auto":
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    else:
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    app.exec()

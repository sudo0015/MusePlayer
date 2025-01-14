import os
import sys
import mutagen
import subprocess
import Res_MusePlayer
from typing import Union
from pathlib import Path
from config import cfg, HELP_URL
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation, QObject, QUrl
from PySide6.QtGui import QIcon, QShortcut, QKeySequence, QColor, QPainter
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QStackedWidget, QVBoxLayout, QLabel, QFileDialog, \
    QButtonGroup, QPushButton, QGraphicsOpacityEffect, QFrame
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from qframelesswindow import FramelessWindow, StandardTitleBar
from qfluentwidgets import SettingCardGroup, PushSettingCard, HyperlinkCard, ScrollArea, \
    ExpandSettingCard, ExpandLayout, Theme, InfoBar, setTheme, setThemeColor, isDarkTheme, SegmentedWidget, \
    ExpandGroupSettingCard, RadioButton, qconfig, ColorConfigItem, FluentIconBase, \
    TransparentDropDownPushButton, RoundMenu, CommandBar, Action, setFont, ImageLabel, FluentStyleSheet, \
    TransparentToolButton, ToolTipFilter, Slider, CaptionLabel, Flyout, FlyoutViewBase, SingleDirectionScrollArea, \
    PrimaryPushButton, BodyLabel, PrimarySplitPushButton, MessageBoxBase, SubtitleLabel, LineEdit, \
    MenuAnimationType, ConfigItem, SwitchButton, IndicatorPosition, CheckableMenu, MenuIndicatorType
from qfluentwidgets.components.dialog_box.color_dialog import HuePanel, ColorCard, BrightnessSlider, HexColorLineEdit, \
    ColorLineEdit, OpacityLineEdit
from qfluentwidgets.components.widgets.flyout import SlideLeftFlyoutAnimationManager
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets.components.dialog_box.mask_dialog_base import MaskDialogBase
from qfluentwidgets.components.settings.setting_card import SettingIconWidget

class ColorDialog(MaskDialogBase):

    colorChanged = Signal(QColor)

    def __init__(self, color, title: str, parent=None, enableAlpha=False):
        super().__init__(parent)
        self.enableAlpha = enableAlpha
        if not enableAlpha:
            color = QColor(color)
            color.setAlpha(255)

        self.oldColor = QColor(color)
        self.color = QColor(color)

        self.scrollArea = SingleDirectionScrollArea(self.widget)
        self.scrollWidget = QWidget(self.scrollArea)

        self.buttonGroup = QFrame(self.widget)
        self.yesButton = PrimaryPushButton(self.tr('确定'), self.buttonGroup)
        self.cancelButton = QPushButton(self.tr('取消'), self.buttonGroup)

        self.titleLabel = QLabel(title, self.scrollWidget)
        self.huePanel = HuePanel(color, self.scrollWidget)
        self.newColorCard = ColorCard(color, self.scrollWidget, enableAlpha)
        self.oldColorCard = ColorCard(color, self.scrollWidget, enableAlpha)
        self.brightSlider = BrightnessSlider(color, self.scrollWidget)

        self.editLabel = QLabel(self.tr('编辑颜色'), self.scrollWidget)
        self.redLabel = QLabel(self.tr('红'), self.scrollWidget)
        self.blueLabel = QLabel(self.tr('蓝'), self.scrollWidget)
        self.greenLabel = QLabel(self.tr('绿'), self.scrollWidget)
        self.opacityLabel = QLabel(self.tr('不透明度'), self.scrollWidget)
        self.hexLineEdit = HexColorLineEdit(color, self.scrollWidget, enableAlpha)
        self.redLineEdit = ColorLineEdit(self.color.red(), self.scrollWidget)
        self.greenLineEdit = ColorLineEdit(self.color.green(), self.scrollWidget)
        self.blueLineEdit = ColorLineEdit(self.color.blue(), self.scrollWidget)
        self.opacityLineEdit = OpacityLineEdit(self.color.alpha(), self.scrollWidget)

        self.vBoxLayout = QVBoxLayout(self.widget)

        self.__initWidget()

    def __initWidget(self):
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea.setViewportMargins(48, 24, 0, 24)
        self.scrollArea.setWidget(self.scrollWidget)

        self.widget.setMaximumSize(488, 696+40*self.enableAlpha)
        self.widget.resize(488, 696+40*self.enableAlpha)
        self.scrollWidget.resize(440, 560+40*self.enableAlpha)
        self.buttonGroup.setFixedSize(486, 81)
        self.yesButton.setFixedWidth(216)
        self.cancelButton.setFixedWidth(216)

        self.setShadowEffect(60, (0, 10), QColor(0, 0, 0, 80))
        self.setMaskColor(QColor(0, 0, 0, 76))

        self.__setQss()
        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        self.huePanel.move(0, 46)
        self.newColorCard.move(288, 46)
        self.oldColorCard.move(288, self.newColorCard.geometry().bottom()+1)
        self.brightSlider.move(0, 324)

        self.editLabel.move(0, 385)
        self.redLineEdit.move(0, 426)
        self.greenLineEdit.move(0, 470)
        self.blueLineEdit.move(0, 515)
        self.redLabel.move(144, 434)
        self.greenLabel.move(144, 478)
        self.blueLabel.move(144, 524)
        self.hexLineEdit.move(196, 381)

        if self.enableAlpha:
            self.opacityLineEdit.move(0, 560)
            self.opacityLabel.move(144, 567)
        else:
            self.opacityLineEdit.hide()
            self.opacityLabel.hide()

        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.addWidget(self.scrollArea, 1)
        self.vBoxLayout.addWidget(self.buttonGroup, 0, Qt.AlignBottom)

        self.yesButton.move(24, 25)
        self.cancelButton.move(250, 25)

    def __setQss(self):
        self.editLabel.setObjectName('editLabel')
        self.titleLabel.setObjectName('titleLabel')
        self.yesButton.setObjectName('yesButton')
        self.cancelButton.setObjectName('cancelButton')
        self.buttonGroup.setObjectName('buttonGroup')
        FluentStyleSheet.COLOR_DIALOG.apply(self)
        self.titleLabel.adjustSize()
        self.editLabel.adjustSize()

    def setColor(self, color, movePicker=True):
        """ set color """
        self.color = QColor(color)
        self.brightSlider.setColor(color)
        self.newColorCard.setColor(color)
        self.hexLineEdit.setColor(color)
        self.redLineEdit.setText(str(color.red()))
        self.blueLineEdit.setText(str(color.blue()))
        self.greenLineEdit.setText(str(color.green()))
        if movePicker:
            self.huePanel.setColor(color)

    def __onHueChanged(self, color):
        """ hue changed slot """
        self.color.setHsv(
            color.hue(), color.saturation(), self.color.value(), self.color.alpha())
        self.setColor(self.color)

    def __onBrightnessChanged(self, color):
        """ brightness changed slot """
        self.color.setHsv(
            self.color.hue(), self.color.saturation(), color.value(), color.alpha())
        self.setColor(self.color, False)

    def __onRedChanged(self, red):
        """ red channel changed slot """
        self.color.setRed(int(red))
        self.setColor(self.color)

    def __onBlueChanged(self, blue):
        """ blue channel changed slot """
        self.color.setBlue(int(blue))
        self.setColor(self.color)

    def __onGreenChanged(self, green):
        """ green channel changed slot """
        self.color.setGreen(int(green))
        self.setColor(self.color)

    def __onOpacityChanged(self, opacity):
        """ opacity channel changed slot """
        self.color.setAlpha(int(int(opacity)/100*255))
        self.setColor(self.color)

    def __onHexColorChanged(self, color):
        """ hex color changed slot """
        self.color.setNamedColor("#" + color)
        self.setColor(self.color)

    def __onYesButtonClicked(self):
        """ yes button clicked slot """
        self.accept()
        if self.color != self.oldColor:
            self.colorChanged.emit(self.color)

    def updateStyle(self):
        """ update style sheet """
        self.setStyle(QApplication.style())
        self.titleLabel.adjustSize()
        self.editLabel.adjustSize()
        self.redLabel.adjustSize()
        self.greenLabel.adjustSize()
        self.blueLabel.adjustSize()
        self.opacityLabel.adjustSize()

    def showEvent(self, e):
        self.updateStyle()
        super().showEvent(e)

    def __connectSignalToSlot(self):
        """ connect signal to slot """
        self.cancelButton.clicked.connect(self.reject)
        self.yesButton.clicked.connect(self.__onYesButtonClicked)

        self.huePanel.colorChanged.connect(self.__onHueChanged)
        self.brightSlider.colorChanged.connect(self.__onBrightnessChanged)

        self.redLineEdit.valueChanged.connect(self.__onRedChanged)
        self.blueLineEdit.valueChanged.connect(self.__onBlueChanged)
        self.greenLineEdit.valueChanged.connect(self.__onGreenChanged)
        self.hexLineEdit.valueChanged.connect(self.__onHexColorChanged)
        self.opacityLineEdit.valueChanged.connect(self.__onOpacityChanged)

class SettingCard(QFrame):
    """ Setting card """

    def __init__(self, icon: Union[str, QIcon, FluentIconBase], title, content=None, parent=None):

        super().__init__(parent=parent)
        self.iconLabel = SettingIconWidget(icon, self)
        self.titleLabel = QLabel(title, self)
        self.contentLabel = QLabel(content or '', self)
        self.hBoxLayout = QHBoxLayout(self)
        self.vBoxLayout = QVBoxLayout()

        if not content:
            self.contentLabel.hide()

        self.setFixedHeight(70 if content else 50)
        self.iconLabel.setFixedSize(16, 16)

        # initialize layout
        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(16, 0, 0, 0)
        self.hBoxLayout.setAlignment(Qt.AlignVCenter)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setAlignment(Qt.AlignVCenter)

        self.hBoxLayout.addWidget(self.iconLabel, 0, Qt.AlignLeft)
        self.hBoxLayout.addSpacing(16)

        self.hBoxLayout.addLayout(self.vBoxLayout)
        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignLeft)
        self.vBoxLayout.addWidget(self.contentLabel, 0, Qt.AlignLeft)

        self.hBoxLayout.addSpacing(16)
        self.hBoxLayout.addStretch(1)

        self.contentLabel.setObjectName('contentLabel')
        FluentStyleSheet.SETTING_CARD.apply(self)

    def setTitle(self, title: str):
        """ set the title of card """
        self.titleLabel.setText(title)

    def setContent(self, content: str):
        """ set the content of card """
        self.contentLabel.setText(content)
        self.contentLabel.setVisible(bool(content))

    def setValue(self, value):
        """ set the value of config item """
        pass

    def setIconSize(self, width: int, height: int):
        """ set the icon fixed size """
        self.iconLabel.setFixedSize(width, height)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)

        if isDarkTheme():
            painter.setBrush(QColor(255, 255, 255, 13))
            painter.setPen(QColor(0, 0, 0, 50))
        else:
            painter.setBrush(QColor(255, 255, 255, 170))
            painter.setPen(QColor(0, 0, 0, 19))

        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)

class SwitchSettingCard(SettingCard):
    """ Setting card with switch button """

    checkedChanged = Signal(bool)

    def __init__(self, icon: Union[str, QIcon, FluentIconBase], title, content=None,
                 configItem: ConfigItem = None, parent=None):

        super().__init__(icon, title, content, parent)
        self.configItem = configItem
        self.switchButton = SwitchButton(self.tr('关'), self, IndicatorPosition.RIGHT)

        if configItem:
            self.setValue(qconfig.get(configItem))
            configItem.valueChanged.connect(self.setValue)

        # add switch button to layout
        self.hBoxLayout.addWidget(self.switchButton, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.switchButton.checkedChanged.connect(self.__onCheckedChanged)

    def __onCheckedChanged(self, isChecked: bool):
        """ switch button checked state changed slot """
        self.setValue(isChecked)
        self.checkedChanged.emit(isChecked)

    def setValue(self, isChecked: bool):
        if self.configItem:
            qconfig.set(self.configItem, isChecked)

        self.switchButton.setChecked(isChecked)
        self.switchButton.setText(
            self.tr('开') if isChecked else self.tr('关'))

    def setChecked(self, isChecked: bool):
        self.setValue(isChecked)

    def isChecked(self):
        return self.switchButton.isChecked()

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


class UrlMessageBox(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel('打开 URL', self)
        self.urlLineEdit = LineEdit(self)

        self.urlLineEdit.setPlaceholderText('输入文件或流的 URL')
        self.urlLineEdit.setClearButtonEnabled(True)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.urlLineEdit)

        self.yesButton.setText('打开')
        self.cancelButton.setText('取消')

        self.widget.setMinimumWidth(350)
        self.yesButton.setDisabled(True)
        self.urlLineEdit.textChanged.connect(self._validateUrl)

    def _validateUrl(self, text):
        self.yesButton.setEnabled(QUrl(text).isValid())


class PlayInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        global path
        self.isLoop = False
        if path:
            self.FileDirectory = path.replace('"', '')
        else:
            self.FileDirectory = ''
        self.vBoxLayout = QVBoxLayout(self)
        self.hBoxLayout = QHBoxLayout(self)
        self.commandBar = CommandBar(self)
        self.addBtn = self.openDropDownButton()
        self.hBoxLayout.addWidget(self.commandBar, 0)
        self.commandBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.commandBar.addWidget(self.addBtn)
        self.commandBar.addSeparator()
        self.commandBar.addAction(Action(FIF.SYNC, '循环', triggered=self.onLoop, checkable=True))
        self.commandBar.addWidget(self.createDropDownButtonSpeed())
        self.commandBar.addSeparator()
        self.addButtonInfo(FIF.INFO, '属性')
        self.addButtonShare(FIF.SHARE, '分享')
        self.standardPlayBar = StandardMediaPlayBar(self)
        self.standardPlayBar.setLoop(True) if self.isLoop else self.standardPlayBar.setLoop(False)
        self.standardPlayBar.volumeButton.setVolume(100)
        self.imgLabel = ImageLabel(self)
        self.imgLabel.clicked.connect(lambda: self.imgLabelMenu())
        if isDarkTheme():
            self.imgLabel.setImage(':/AlbumDark.png')
        else:
            self.imgLabel.setImage(':/AlbumLight.png')
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
        self.setQss()
        cfg.themeChanged.connect(self.setQss)
        if self.FileDirectory:
            self.Play(True)

    def openDropDownButton(self):
        button = PrimarySplitPushButton(FIF.ADD, '打开', self)
        button.setFixedWidth(108)
        button.clicked.connect(lambda: self.filePick())
        self.fileAction = Action(FIF.DOCUMENT, '文件', shortcut='Ctrl+O')
        self.folderAction = Action(FIF.FOLDER, '文件夹', shortcut='Ctrl+Shift+O')
        self.urlAction = Action(FIF.GLOBE, 'URL', shortcut='Ctrl+U')
        self.videoAction = Action(FIF.VIDEO, '听视频', shortcut='Ctrl+V')
        self.newWindowAction = Action(FIF.ADD_TO, '新窗口', shortcut='Ctrl+N')
        self.fileAction.triggered.connect(lambda: self.filePick())
        '''
        self.folderAction.triggered.connect()
        self.videoAction.triggered.connect()
        self.newWindowAction.triggered.connect()
        '''
        menu = RoundMenu(parent=self)
        menu.addActions([self.fileAction, self.folderAction, self.urlAction,])
        menu.addSeparator()
        menu.addAction(self.videoAction)
        menu.addSeparator()
        menu.addAction(self.newWindowAction)
        button.setFlyout(menu)
        return button

    def imgLabelMenu(self):
        print("")
        """NEED REPLACE"""

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
        setFont(button, 12)
        button.setFixedHeight(34)
        playSpeedA = Action('0.25 ⨯', shortcut='Ctrl+Shift+A')
        playSpeedS = Action('0.5 ⨯', shortcut='Ctrl+Shift+S')
        playSpeedD = Action('1 ⨯', shortcut='Ctrl+Shift+D')
        playSpeedF = Action('1.25 ⨯', shortcut='Ctrl+Shift+F')
        playSpeedG = Action('1.5 ⨯', shortcut='Ctrl+Shift+G')
        playSpeedH = Action('2 ⨯', shortcut='Ctrl+Shift+H')
        playSpeedA.triggered.connect(lambda: self.setPlaySpeed(0))
        playSpeedS.triggered.connect(lambda: self.setPlaySpeed(1))
        playSpeedD.triggered.connect(lambda: self.setPlaySpeed(2))
        playSpeedF.triggered.connect(lambda: self.setPlaySpeed(3))
        playSpeedG.triggered.connect(lambda: self.setPlaySpeed(4))
        playSpeedH.triggered.connect(lambda: self.setPlaySpeed(5))
        self.speedMenu = CheckableMenu(parent=self, indicatorType=MenuIndicatorType.RADIO)
        self.speedMenu.addActions([playSpeedA, playSpeedS, playSpeedD,
                                   playSpeedF, playSpeedG, playSpeedH,])
        for i in range(6):
            self.speedMenu.actions()[i].setCheckable(True)
        self.speedMenu.actions()[2].setChecked(True)
        button.setMenu(self.speedMenu)
        return button

    def setPlaySpeed(self, speedIndex):
        if speedIndex == 0:
            self.standardPlayBar.player.setPlaybackRate(0.25)
            for i in range(6):
                if i == speedIndex:
                    self.speedMenu.actions()[i].setChecked(True)
                else:
                    self.speedMenu.actions()[i].setChecked(False)
        if speedIndex == 1:
            self.standardPlayBar.player.setPlaybackRate(0.5)
            for i in range(6):
                if i == speedIndex:
                    self.speedMenu.actions()[i].setChecked(True)
                else:
                    self.speedMenu.actions()[i].setChecked(False)
        if speedIndex == 2:
            self.standardPlayBar.player.setPlaybackRate(1)
            for i in range(6):
                if i == speedIndex:
                    self.speedMenu.actions()[i].setChecked(True)
                else:
                    self.speedMenu.actions()[i].setChecked(False)
        if speedIndex == 3:
            self.standardPlayBar.player.setPlaybackRate(1.25)
            for i in range(6):
                if i == speedIndex:
                    self.speedMenu.actions()[i].setChecked(True)
                else:
                    self.speedMenu.actions()[i].setChecked(False)
        if speedIndex == 4:
            self.standardPlayBar.player.setPlaybackRate(1.5)
            for i in range(6):
                if i == speedIndex:
                    self.speedMenu.actions()[i].setChecked(True)
                else:
                    self.speedMenu.actions()[i].setChecked(False)
        if speedIndex == 5:
            self.standardPlayBar.player.setPlaybackRate(2)
            for i in range(6):
                if i == speedIndex:
                    self.speedMenu.actions()[i].setChecked(True)
                else:
                    self.speedMenu.actions()[i].setChecked(False)

    def setQss(self):
        if isDarkTheme():
            self.setStyleSheet(
                "MinimizeButton {qproperty-normalColor: white; qproperty-normalBackgroundColor: transparent; qproperty-hoverColor: white; qproperty-hoverBackgroundColor: rgba(255, 255, 255, 26); qproperty-pressedColor: white; qproperty-pressedBackgroundColor: rgba(255, 255, 255, 51)}"
                "MaximizeButton {qproperty-normalColor: white; qproperty-normalBackgroundColor: transparent; qproperty-hoverColor: white; qproperty-hoverBackgroundColor: rgba(255, 255, 255, 26); qproperty-pressedColor: white; qproperty-pressedBackgroundColor: rgba(255, 255, 255, 51)}"
                "CloseButton {qproperty-normalColor: white; qproperty-normalBackgroundColor: transparent;}"
                "StandardTitleBar > QLabel {color: white;}"
                )
        else:
            self.setStyleSheet(
                "MinimizeButton {qproperty-normalColor: black; qproperty-normalBackgroundColor: transparent; qproperty-hoverColor: black; qproperty-hoverBackgroundColor: rgba(0, 0, 0, 26); qproperty-pressedColor: black; qproperty-pressedBackgroundColor: rgba(0, 0, 0, 51)}"
                "MaximizeButton {qproperty-normalColor: black; qproperty-normalBackgroundColor: transparent; qproperty-hoverColor: black; qproperty-hoverBackgroundColor: rgba(0, 0, 0, 26); qproperty-pressedColor: black; qproperty-pressedBackgroundColor: rgba(0, 0, 0, 51)}"
                "CloseButton {qproperty-normalColor: black; qproperty-normalBackgroundColor: transparent;}"
                "StandardTitleBar > QLabel {color: black;}"
                )

    def onLoop(self, isChecked):
        if isChecked:
            self.isLoop = True
        else:
            self.isLoop = False
        self.standardPlayBar.setLoop(True) if self.isLoop else self.standardPlayBar.setLoop(False)

    def OpenWith(self):
        args = ["C:\\Windows\\System32\\OpenWith.exe", self.FileDirectory.replace("/", "\\")]
        subprocess.run(args, shell=True)

    def Play(self, isLocal):
        self.standardPlayBar.deleteLater()
        self.standardPlayBar = StandardMediaPlayBar(self)
        self.standardPlayBar.volumeButton.setVolume(100)
        self.standardPlayBar.setLoop(True) if self.isLoop else self.standardPlayBar.setLoop(False)
        self.hoLayout.addWidget(self.standardPlayBar)
        if isLocal:
            self.standardPlayBar.player.setSource(QUrl.fromLocalFile(str(Path(self.FileDirectory).absolute())))
        else:
            self.standardPlayBar.player.setSource(QUrl(self.FileDirectory))
        self.standardPlayBar.play()
        try:
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
                with open(str(Path.home()).replace('\\', '/') + '/.MusePlayer/img/cover.jpg', 'wb') as img:
                    img.write(self.cover)
                self.imgLabel.setImage(str(Path.home()).replace('\\', '/') + '/.MusePlayer/img/cover.jpg')
                self.imgLabel.setBorderRadius(10, 10, 10, 10)
                self.imgLabel.setFixedSize(100, 100)
            else:
                if isDarkTheme():
                    self.imgLabel.setImage(':/AlbumDark.png')
                else:
                    self.imgLabel.setImage(':/AlbumLight.png')
                self.imgLabel.setBorderRadius(10, 10, 10, 10)
                self.imgLabel.setFixedSize(100, 100)
        except:
            if isDarkTheme():
                self.imgLabel.setImage(':/AlbumDark.png')
            else:
                self.imgLabel.setImage(':/AlbumLight.png')
            self.imgLabel.setBorderRadius(10, 10, 10, 10)
            self.imgLabel.setFixedSize(100, 100)


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
        self.FileDirectory = QFileDialog.getOpenFileName(self, "打开文件", cfg.musicFolder.value,"音频文件 (*.mp3 *.acc *.wma *.wav *.ogg *.m4a *.ape *.flac *.cue);;所有文件 (*.*)")[0]
        if self.FileDirectory:
            self.Play(True)


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
        """TODO"""
        self.aboutCard.viewLayout.addWidget(
            BodyLabel("    MusePlayer (v3.2.1)\n    Copyright © 2024 BUG STUDIO. All rights reserved."))
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
        if isDarkTheme():
            self.setStyleSheet("SettingInterface, #scrollWidget {background-color: rgb(39, 39, 39);}"
                               "QScrollArea {border: none; background-color: rgb(39, 39, 39);}"
                               "QLabel#settingLabel {font: 33px 'Microsoft YaHei Light'; background-color: transparent; color: white;}"
                               )
        else:
            self.setStyleSheet("SettingInterface, #scrollWidget {background-color: rgb(249, 249, 249);}"
                               "QScrollArea {background-color: rgb(249, 249, 249); border: none;}"
                               "QLabel#settingLabel {font: 33px 'Microsoft YaHei Light'; background-color: transparent;}"
                               )

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
        self.setWindowOpacity(0.97)
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
        self.setWindowIcon(QIcon(":/icon.png"))
        self.setWindowTitle("MusePlayer")
        self.resize(730, 260)
        desktop = QApplication.screens()[0].size()
        self.move(desktop.width() // 2 - self.width() // 2, desktop.height() // 2 - self.height() // 2)
        self.titleBar.raise_()
        self.setQss()
        cfg.themeChanged.connect(self.setQss)
        self.playInterface.urlAction.triggered.connect(lambda: self.openUrl())
        self.KeyOpenFile()
        self.KeyOpenFolder()
        self.KeyOpenUrl()
        self.KeyPlayAndPause()
        self.KeyForward()
        self.KeyBackward()
        self.KeyQuickForward()
        self.KeyQuickBackward()
        self.KeySetting()
        self.KeyPage1()
        self.KeyPage2()
        self.KeyPage3()

    def KeyOpenFile(self):
        shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        shortcut.activated.connect(lambda: self.playInterface.filePick())

    def KeyOpenFolder(self):
        shortcut = QShortcut(QKeySequence("Ctrl+Shift+O"), self)
        shortcut.activated.connect(lambda: print("open folder"))

    def KeyOpenUrl(self):
        shortcut = QShortcut(QKeySequence("Ctrl+U"), self)
        shortcut.activated.connect(lambda: self.openUrl())

    def KeyPlayAndPause(self):
        shortcut = QShortcut(QKeySequence("Space"), self)
        shortcut.activated.connect(lambda: self.playInterface.standardPlayBar.togglePlayState())

    def KeyForward(self):
        shortcut = QShortcut(QKeySequence("Right"), self)
        shortcut.activated.connect(lambda: self.playInterface.standardPlayBar.skipForward(5000))

    def KeyBackward(self):
        shortcut = QShortcut(QKeySequence("Left"), self)
        shortcut.activated.connect(lambda: self.playInterface.standardPlayBar.skipBack(5000))

    def KeyQuickForward(self):
        shortcut = QShortcut(QKeySequence("Shift+Right"), self)
        shortcut.activated.connect(lambda: self.playInterface.standardPlayBar.skipForward(30000))

    def KeyQuickBackward(self):
        shortcut = QShortcut(QKeySequence("Shift+Left"), self)
        shortcut.activated.connect(lambda: self.playInterface.standardPlayBar.skipBack(10000))

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

    def openUrl(self):
        w = UrlMessageBox(self)
        if w.exec():
            self.playInterface.FileDirectory = w.urlLineEdit.text()
            self.playInterface.Play(False)

    def setQss(self):
        if isDarkTheme():
            self.setStyleSheet("MinimizeButton {qproperty-normalColor: white; qproperty-normalBackgroundColor: transparent; qproperty-hoverColor: white; qproperty-hoverBackgroundColor: rgba(255, 255, 255, 26); qproperty-pressedColor: white; qproperty-pressedBackgroundColor: rgba(255, 255, 255, 51)}"
                               "MaximizeButton {qproperty-normalColor: white; qproperty-normalBackgroundColor: transparent; qproperty-hoverColor: white; qproperty-hoverBackgroundColor: rgba(255, 255, 255, 26); qproperty-pressedColor: white; qproperty-pressedBackgroundColor: rgba(255, 255, 255, 51)}"
                               "CloseButton {qproperty-normalColor: white; qproperty-normalBackgroundColor: transparent;}"
                               "StandardTitleBar > QLabel {color: white;}"
                               )
        else:
            self.setStyleSheet("MinimizeButton {qproperty-normalColor: black; qproperty-normalBackgroundColor: transparent; qproperty-hoverColor: black; qproperty-hoverBackgroundColor: rgba(0, 0, 0, 26); qproperty-pressedColor: black; qproperty-pressedBackgroundColor: rgba(0, 0, 0, 51)}"
                               "MaximizeButton {qproperty-normalColor: black; qproperty-normalBackgroundColor: transparent; qproperty-hoverColor: black; qproperty-hoverBackgroundColor: rgba(0, 0, 0, 26); qproperty-pressedColor: black; qproperty-pressedBackgroundColor: rgba(0, 0, 0, 51)}"
                               "CloseButton {qproperty-normalColor: black; qproperty-normalBackgroundColor: transparent;}"
                               "StandardTitleBar > QLabel {color: black;}"
                               )


if __name__ == '__main__':
    if cfg.get(cfg.dpiScale) == "Auto":
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    else:
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))
    if len(sys.argv) == 2:
        path = sys.argv[1]
    else:
        path = ''
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    app.exec()

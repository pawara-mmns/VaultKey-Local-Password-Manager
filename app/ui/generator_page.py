"""Interactive cryptographically secure password generator page."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.components.page_widgets import PageHeader
from app.security.password_generator import (
    DEFAULT_PASSWORD_LENGTH,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    PasswordGenerationError,
    PasswordGenerator,
)
from app.security.password_strength import StrengthResult, assess_generated_password


class PasswordOptionCard(QFrame):
    """Compact generator option matching VaultKey's card design."""

    def __init__(self, title: str, example: str) -> None:
        super().__init__(objectName="generatorOptionCard")
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 11, 14, 11)
        self.checkbox = QCheckBox(title, objectName="generatorCheckbox")
        self.checkbox.setChecked(True)
        example_label = QLabel(example, objectName="optionExample")
        row.addWidget(self.checkbox)
        row.addStretch(1)
        row.addWidget(example_label)


class GeneratorPage(QWidget):
    """Generate, assess, and copy passwords without persisting them."""

    save_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        self._generator = PasswordGenerator()

        self._copy_feedback_timer = QTimer(self)
        self._copy_feedback_timer.setSingleShot(True)
        self._copy_feedback_timer.setInterval(1800)
        self._copy_feedback_timer.timeout.connect(self._reset_copy_feedback)

        self._length_debounce_timer = QTimer(self)
        self._length_debounce_timer.setSingleShot(True)
        self._length_debounce_timer.setInterval(260)
        self._length_debounce_timer.timeout.connect(self.generate_password)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(objectName="pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget(objectName="pageContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(44, 36, 44, 40)
        layout.setSpacing(24)
        layout.addWidget(
            PageHeader(
                "Password Generator",
                "Create strong, unique passwords instantly—entirely on this device.",
            )
        )

        card = QFrame(objectName="generatorCard")
        card.setMaximumWidth(860)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(22)
        self._build_output(card_layout)
        self._build_strength(card_layout)
        self._build_length(card_layout)
        self._build_options(card_layout)
        self._build_actions(card_layout)

        layout.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        scroll.setWidget(content)

        self._connect_signals()
        self.generate_password()

    def _build_output(self, layout: QVBoxLayout) -> None:
        layout.addWidget(QLabel("Generated password", objectName="fieldLabel"))
        output_card = QFrame(objectName="generatorOutputCard")
        output_layout = QHBoxLayout(output_card)
        output_layout.setContentsMargins(18, 13, 12, 13)
        output_layout.setSpacing(12)

        self.password_output = QLineEdit(objectName="generatedPassword")
        self.password_output.setReadOnly(True)
        self.password_output.setAccessibleName("Generated password")
        self.password_output.setToolTip("Select the password or copy it to the clipboard")
        self.copy_button = QPushButton("Copy", objectName="generatorCopyButton")
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_button.setAccessibleName("Copy generated password")
        output_layout.addWidget(self.password_output, 1)
        output_layout.addWidget(self.copy_button)
        layout.addWidget(output_card)

    def _build_strength(self, layout: QVBoxLayout) -> None:
        heading = QHBoxLayout()
        heading.addWidget(QLabel("Password strength", objectName="fieldLabel"))
        heading.addStretch(1)
        self.strength_label = QLabel("Very Weak", objectName="generatorStrengthLabel")
        self.strength_label.setProperty("strength", 0)
        heading.addWidget(self.strength_label)

        self.strength_bar = QProgressBar(objectName="generatorStrengthBar")
        self.strength_bar.setRange(0, 100)
        self.strength_bar.setValue(0)
        self.strength_bar.setTextVisible(False)
        self.strength_bar.setProperty("strength", 0)
        self.entropy_label = QLabel("Approx. entropy: 0 bits", objectName="entropyLabel")

        layout.addLayout(heading)
        layout.addWidget(self.strength_bar)
        layout.addWidget(self.entropy_label)

    def _build_length(self, layout: QVBoxLayout) -> None:
        heading = QHBoxLayout()
        heading.addWidget(QLabel("Password length", objectName="fieldLabel"))
        heading.addStretch(1)
        self.length_value = QLabel(str(DEFAULT_PASSWORD_LENGTH), objectName="lengthBadge")
        heading.addWidget(self.length_value)

        slider_row = QHBoxLayout()
        minimum = QLabel(str(MIN_PASSWORD_LENGTH), objectName="sliderBound")
        maximum = QLabel(str(MAX_PASSWORD_LENGTH), objectName="sliderBound")
        self.length_slider = QSlider(Qt.Orientation.Horizontal, objectName="lengthSlider")
        self.length_slider.setRange(MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH)
        self.length_slider.setValue(DEFAULT_PASSWORD_LENGTH)
        self.length_slider.setSingleStep(1)
        self.length_slider.setPageStep(4)
        self.length_slider.setAccessibleName("Password length")
        slider_row.addWidget(minimum)
        slider_row.addWidget(self.length_slider, 1)
        slider_row.addWidget(maximum)

        layout.addLayout(heading)
        layout.addLayout(slider_row)

    def _build_options(self, layout: QVBoxLayout) -> None:
        layout.addWidget(QLabel("Character types", objectName="generatorSectionLabel"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)

        self.uppercase_option = PasswordOptionCard("Uppercase", "A–Z")
        self.lowercase_option = PasswordOptionCard("Lowercase", "a–z")
        self.numbers_option = PasswordOptionCard("Numbers", "0–9")
        self.symbols_option = PasswordOptionCard("Symbols", "!@#$%…")
        for index, widget in enumerate(self._option_cards()):
            grid.addWidget(widget, index // 2, index % 2)
            grid.setColumnStretch(index % 2, 1)
        layout.addLayout(grid)

        layout.addWidget(QLabel("Options", objectName="generatorSectionLabel"))
        self.ambiguous_option = QCheckBox(
            "Exclude ambiguous characters  (0, O, o, 1, l, I)",
            objectName="generatorCheckbox",
        )
        layout.addWidget(self.ambiguous_option)

    def _build_actions(self, layout: QVBoxLayout) -> None:
        self.feedback_label = QLabel(objectName="generatorFeedback")
        self.feedback_label.setProperty("state", "info")
        self.feedback_label.setWordWrap(True)
        self.feedback_label.hide()

        action_row = QHBoxLayout()
        shortcut_hint = QLabel("Ctrl + G to generate", objectName="shortcutHint")
        self.generate_button = QPushButton(
            "↻  Generate New Password", objectName="primaryButton"
        )
        self.save_button = QPushButton("Save to Vault", objectName="secondaryButton")
        self.generate_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_button.setAccessibleName("Generate new password")
        action_row.addWidget(shortcut_hint)
        action_row.addStretch(1)
        action_row.addWidget(self.save_button)
        action_row.addWidget(self.generate_button)

        layout.addWidget(self.feedback_label)
        layout.addLayout(action_row)

    def _option_cards(self) -> tuple[PasswordOptionCard, ...]:
        return (
            self.uppercase_option,
            self.lowercase_option,
            self.numbers_option,
            self.symbols_option,
        )

    def _category_checkboxes(self) -> tuple[QCheckBox, ...]:
        return tuple(card.checkbox for card in self._option_cards())

    def _connect_signals(self) -> None:
        self.length_slider.valueChanged.connect(self._length_changed)
        self.length_slider.sliderReleased.connect(self._length_released)
        for option in self._category_checkboxes():
            option.toggled.connect(self._options_changed)
        self.ambiguous_option.toggled.connect(
            lambda checked=False: self.generate_password()
        )
        self.generate_button.clicked.connect(
            lambda checked=False: self.generate_password()
        )
        self.copy_button.clicked.connect(lambda checked=False: self.copy_password())
        self.save_button.clicked.connect(
            lambda checked=False: self.save_requested.emit(self.password_output.text())
        )
        self.generate_shortcut = QShortcut(QKeySequence("Ctrl+G"), self)
        self.generate_shortcut.activated.connect(self.generate_password)

    def _length_changed(self, value: int) -> None:
        self.length_value.setText(str(value))
        if not self.length_slider.isSliderDown():
            self._length_debounce_timer.start()

    def _length_released(self) -> None:
        self._length_debounce_timer.stop()
        self.generate_password()

    def _options_changed(self) -> None:
        if not any(option.isChecked() for option in self._category_checkboxes()):
            self._show_feedback("Select at least one character type.", error=True)
            self.generate_button.setEnabled(False)
            return
        self.generate_button.setEnabled(True)
        self.generate_password()

    def _current_options(self) -> tuple[int, bool, bool, bool, bool, bool]:
        uppercase, lowercase, numbers, symbols = self._category_checkboxes()
        return (
            self.length_slider.value(),
            uppercase.isChecked(),
            lowercase.isChecked(),
            numbers.isChecked(),
            symbols.isChecked(),
            self.ambiguous_option.isChecked(),
        )

    def generate_password(self) -> None:
        """Generate from the current controls and refresh strength feedback."""
        length, uppercase, lowercase, numbers, symbols, exclude_ambiguous = (
            self._current_options()
        )
        try:
            password = self._generator.generate(
                length,
                uppercase,
                lowercase,
                numbers,
                symbols,
                exclude_ambiguous,
            )
            pool_size = self._generator.character_pool_size(
                uppercase=uppercase,
                lowercase=lowercase,
                numbers=numbers,
                symbols=symbols,
                exclude_ambiguous=exclude_ambiguous,
            )
            strength = assess_generated_password(password, pool_size)
        except PasswordGenerationError as error:
            self._show_feedback(str(error), error=True)
            return
        except Exception:
            self._show_feedback("VaultKey could not generate a password. Try again.", error=True)
            return

        self.password_output.setText(password)
        self.password_output.setCursorPosition(0)
        self.copy_button.setEnabled(True)
        self.generate_button.setEnabled(True)
        self._update_strength(strength)
        self._clear_feedback()

    def copy_password(self) -> None:
        """Copy the current value without logging or persisting it."""
        password = self.password_output.text()
        if not password:
            self._show_feedback("Generate a password before copying.", error=True)
            return
        try:
            QGuiApplication.clipboard().setText(password)
        except Exception:
            self._show_feedback("VaultKey could not access the clipboard.", error=True)
            return
        self.copy_button.setText("Copied ✓")
        self.copy_button.setProperty("copied", True)
        self.copy_button.style().unpolish(self.copy_button)
        self.copy_button.style().polish(self.copy_button)
        self._show_feedback("Password copied to clipboard.")
        self._copy_feedback_timer.start()

    def _update_strength(self, result: StrengthResult) -> None:
        self.strength_label.setText(result.label)
        self.strength_label.setProperty("strength", result.level)
        self.strength_bar.setProperty("strength", result.level)
        self.strength_bar.setValue(result.percent)
        entropy = result.entropy_bits or 0.0
        self.entropy_label.setText(f"Approx. entropy: {entropy:.0f} bits")
        for widget in (self.strength_label, self.strength_bar):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def _show_feedback(self, message: str, *, error: bool = False) -> None:
        self.feedback_label.setText(message)
        self.feedback_label.setProperty("state", "error" if error else "success")
        self.feedback_label.style().unpolish(self.feedback_label)
        self.feedback_label.style().polish(self.feedback_label)
        self.feedback_label.show()

    def _clear_feedback(self) -> None:
        self.feedback_label.clear()
        self.feedback_label.hide()

    def _reset_copy_feedback(self) -> None:
        self.copy_button.setText("Copy")
        self.copy_button.setProperty("copied", False)
        self.copy_button.style().unpolish(self.copy_button)
        self.copy_button.style().polish(self.copy_button)
        if self.feedback_label.property("state") == "success":
            self._clear_feedback()

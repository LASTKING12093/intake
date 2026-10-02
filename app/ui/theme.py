from app.ui.tokens import COLORS as C
from app.ui.assets import font_family

def stylesheet(theme='Dark'):
    return f'''
    * {{ font-family: '{font_family()}'; font-size: 14px; font-weight: 400; color: {C['text']}; }}
    QMainWindow, QDialog, QWidget#page, QWidget#shell, QWidget#header {{ background: {C['background']}; }}
    QWidget#sidebar {{ background: {C['sidebar']}; border-right: 1px solid #232427; }}
    QFrame#card, QFrame#empty {{ background: {C['surface']}; border: 1px solid #202020; border-radius: 16px; }}
    QLabel {{ background: transparent; border: none; }}
    QLabel#title {{ font-size: 28px; font-weight: 600; letter-spacing: -1px; }}
    QLabel#homeHeading {{ font-size: 38px; font-weight: 500; letter-spacing: -1px; }}
    QLabel#platformHint {{ font-size: 12px; color: #777777; padding-left: 4px; }}
    QLabel#tagline {{ font-size: 16px; color: #949494; }}
    QLabel#brand {{ font-size: 16px; font-weight: 500; letter-spacing: 2px; }}
    QLabel#muted, QLabel#subtitle {{ color: {C['muted']}; }}
    QLabel#eyebrow {{ color: #999999; font-size: 10px; letter-spacing: 2px; }}
    QLabel#cardTitle {{ font-size: 18px; font-weight: 500; }}
    QLabel#status {{ color: #dddddd; font-size: 14px; }}
    QLabel#thumb {{ background: #161616; border-radius: 10px; color: #afafa8; font-size: 24px; }}
    QPushButton {{ background: {C['field']}; border: 1px solid {C['edge']}; border-radius: 12px; padding: 0px 20px; font-size: 14px; font-weight: 500; }}
    QPushButton:hover {{ background: #222222; border-color: #626262; }}
    QPushButton:pressed {{ background: #303030; }}
    QPushButton:focus {{ border: 1px solid #ffffff; }}
    QPushButton:disabled {{ color: #727571; border-color: #292b2e; }}
    QPushButton#primary {{ background: #ffffff; color: #080808; font-weight: 500; border: 1px solid #ffffff; }}
    QPushButton#primary:hover {{ background: #ffffff; }}
    QPushButton#primary:pressed {{ background: #d8d8d8; }}
    QPushButton#nav {{ text-align: center; padding: 0px 12px; border: 1px solid transparent; background: transparent; color: #a3a3a3; }}
    QPushButton#nav:checked {{ color: #ffffff; }}
    QPushButton#nav:focus {{ border-color: transparent; color: #ffffff; }}
    QPushButton#quiet {{ background: transparent; border-color: transparent; color: #aaaaaa; }}
    QPushButton#source {{ background: transparent; border: 1px solid transparent; padding: 0px 24px 0px 12px; color: #eeeeee; }}
    QPushButton#quiet:hover, QPushButton#source:hover {{ color: #ffffff; background: #161616; }}
    QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {{ background: #111111; border: 1px solid #2a2a2a; border-radius: 9px; padding: 9px; selection-background-color: #444444; }}
    QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: #b8b9b1; }}
    QPlainTextEdit#url {{ background: transparent; border: none; font-size: 16px; padding: 8px 2px; }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{ background: #111111; selection-background-color: #444640; padding: 6px; border: 1px solid #55574f; }}
    QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 6px; }}
    QScrollBar::handle:vertical {{ background: #3d3f40; border-radius: 3px; min-height: 30px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QProgressBar {{ background: #202020; border: none; border-radius: 2px; min-height: 4px; max-height: 4px; }}
    QProgressBar::chunk {{ background: #ffffff; border-radius: 2px; }}
    QCheckBox {{ spacing: 9px; color: #bdbdbd; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid #6c6f68; border-radius: 4px; background: #141414; }}
    QCheckBox::indicator:checked {{ background: #ffffff; border: 3px solid #777777; }}
    QTableWidget {{ background: #0c0c0c; alternate-background-color: #141414; gridline-color: #2a2a2a; border: 1px solid #2a2a2a; border-radius: 10px; }}
    QHeaderView::section {{ background: #141414; padding: 10px; border: none; color: #a3a3a3; }}
    QGroupBox {{ border: 1px solid #292b2f; border-radius: 12px; margin-top: 22px; padding: 22px 14px 14px; font-weight: 600; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #bdbdbd; }}
    QMenu {{ background: #111111; border: 1px solid #5a5c57; border-radius: 12px; padding: 8px; }}
    QMenu::item {{ padding: 10px 26px 10px 14px; border-radius: 7px; }}
    QMenu::item:selected {{ background: #464842; color: #ffffff; }}
    QToolTip {{ background: #161616; color: #ffffff; border: 1px solid #626262; padding: 6px; }}
    '''

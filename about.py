from PyQt4.QtGui import QDialog, QDialogButtonBox, QLabel, QVBoxLayout
from PyQt4.QtCore import Qt

from aqt import mw

from irx._version import __version__


def showAbout():
    dialog = QDialog(mw)

    label = QLabel()
    text = '''
<div style="text-align: center">
<p style="font-weight: bold; font-size: 16px;">Incremental Reading eXperimental (based on v%s)</p>
<p style="font-size: 14px;">Special thanks to Luo Li-Yan who maintains the original version of this addon</p>
<p style="font-size: 14px;">And other contributors: Tiago Barroso, Frank Kmiec, Aleksej</p>
<hr/>
<p style="font-size: 16px;"> This is nowhere near a 'stable addon', please use the <a href="https://ankiweb.net/shared/info/935264945">original addon</a> for that sort of thing</p>
<p style="font-size: 14px"> This is just something I threw together out of necessity, in a short amount of time, with basically no idea of what I was doing, I just wanted the features in v4 of this addon but on my ANKI v2</p>
</div>''' % __version__
    label.setText(text)
    label.setAlignment(Qt.AlignCenter)

    buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
    buttonBox.accepted.connect(dialog.accept)

    layout = QVBoxLayout()
    layout.addWidget(label)
    layout.addWidget(buttonBox)

    dialog.setLayout(layout)
    dialog.setWindowTitle('About')
    dialog.exec_()

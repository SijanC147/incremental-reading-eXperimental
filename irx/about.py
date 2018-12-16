# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from PyQt4.QtGui import QDialog, QDialogButtonBox, QLabel, QVBoxLayout
from PyQt4.QtCore import Qt

from aqt import mw

from irx._version import __version__
from irx.util import db_log

IR_ORIGINAL_GITHUB_URL = 'https://github.com/luoliyan/incremental-reading'
IRX_GITHUB_URL = "https://github.com/SijanC147/incremental-reading-eXperimental"


def showAbout():
    dialog = QDialog(mw)

    label = QLabel()
    text = '''
<div style="text-align: center">
<p style="font-weight: bold; font-size: 16px;">Incremental Reading 3 eXperimental</p>
<p> v3.8.3x-beta </p>
<p> Sean Bugeja </p>
<p> <a href="{0}">Github</a> </p>
<hr/>
<p>Everything in this add-on is inspired by the incredible work of </p>
<p>Joseph Lorimer</p>
<p>Tiago Barroso, Frank Kmiec, Aleksej, Christian Weiß, Timothée Chauvin</p>
<p>Who actively maintain the <a href="{1}">original IR add-on</a> this builds on.</p>
<hr/>
<p>The motivation behind this add-on was initially trying to port some of the v4 features to the</p>
<p>ANKI2 compatible v3 version, for those who, like myself, aren't ready to let go of some ANKI2 addons.</p>
<p>Consider everything in this add-on <i>experimental and barely functional</i>, this was a learning experience</p> 
<p>more than anything, however I will try my best to maintain and build on it moving forward.</p>
<p>I will be taking a break from it for some time following this release due to other obligations, but I figured maybe</p>
<p>if some people try it out I could get some feedback and have issues ready to fix when I pick it up again.</p>
<p>Any and all input is greatly appreciated.</p>
</div>'''.format(IRX_GITHUB_URL, IR_ORIGINAL_GITHUB_URL)
    label.setText(text)
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet(
        """
        QLabel  {
            font-size: 14px;
        }
    """
    )

    label.setOpenExternalLinks(True)
    buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
    buttonBox.accepted.connect(dialog.accept)

    layout = QVBoxLayout()
    layout.addWidget(label)
    layout.addWidget(buttonBox)

    dialog.setLayout(layout)
    dialog.setWindowTitle('About IR3X')
    dialog.exec_()

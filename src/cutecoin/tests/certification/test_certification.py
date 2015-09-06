import sys
import unittest
import asyncio
import quamash
import time
import logging
from ucoinpy.documents.peer import BMAEndpoint as PyBMAEndpoint
from PyQt5.QtWidgets import QDialog, QDialogButtonBox
from PyQt5.QtCore import QLocale, Qt
from PyQt5.QtTest import QTest
from cutecoin.tests.mocks.bma import init_new_community
from cutecoin.tests.mocks.access_manager import MockNetworkAccessManager
from cutecoin.core.registry.identities import IdentitiesRegistry
from cutecoin.gui.certification import CertificationDialog
from cutecoin.gui.password_asker import PasswordAskerDialog
from cutecoin.core.app import Application
from cutecoin.core import Account, Community, Wallet
from cutecoin.core.net import Network, Node
from cutecoin.core.net.endpoint import BMAEndpoint
from cutecoin.core.net.api.bma.access import BmaAccess
from cutecoin.tests import get_application
from cutecoin.core.net.api import bma as qtbma


class TestCertificationDialog(unittest.TestCase):
    def setUp(self):
        self.qapplication = get_application()
        self.network_manager = MockNetworkAccessManager()
        QLocale.setDefault(QLocale("en_GB"))
        self.lp = quamash.QEventLoop(self.qapplication)
        asyncio.set_event_loop(self.lp)
        self.identities_registry = IdentitiesRegistry()

        self.application = Application(self.qapplication, self.lp, self.network_manager, self.identities_registry)
        self.application.preferences['notifications'] = False

        self.endpoint = BMAEndpoint(PyBMAEndpoint("", "127.0.0.1", "", 50000))
        self.node = Node(self.network_manager, "test_currency", [self.endpoint],
                         "", "HnFcSms8jzwngtVomTTnzudZx7SHUQY8sVE1y8yBmULk",
                         qtbma.blockchain.Block.null_value, Node.ONLINE,
                         time.time(), {}, "ucoin", "0.14.0", 0)
        self.network = Network.create(self.network_manager, self.node)
        self.bma_access = BmaAccess.create(self.network)
        self.community = Community("test_currency", self.network, self.bma_access)

        self.wallet = Wallet(0, "7Aqw6Efa9EzE7gtsc8SveLLrM7gm6NEGoywSv4FJx6pZ",
                             "Wallet 1", self.identities_registry)

        # Salt/password : "testcutecoin/testcutecoin"
        # Pubkey : 7Aqw6Efa9EzE7gtsc8SveLLrM7gm6NEGoywSv4FJx6pZ
        self.account = Account("testcutecoin", "7Aqw6Efa9EzE7gtsc8SveLLrM7gm6NEGoywSv4FJx6pZ",
                               "john", [self.community], [self.wallet], [], self.identities_registry)

        self.password_asker = PasswordAskerDialog(self.account)
        self.password_asker.password = "testcutecoin"
        self.password_asker.remember = True

    def tearDown(self):
        try:
            self.lp.close()
        finally:
            asyncio.set_event_loop(None)

    def test_certification_init_community(self):
        mock = init_new_community.get_mock()
        logging.debug(mock.pretend_url)
        certification_dialog = CertificationDialog(self.application,
                                                   self.account,
                                                   self.password_asker)

        @asyncio.coroutine
        def open_dialog(certification_dialog):
            result = yield from certification_dialog.async_exec()
            self.assertEqual(result, QDialog.Accepted)

        def close_dialog():
            if certification_dialog.isVisible():
                certification_dialog.close()

        @asyncio.coroutine
        def exec_test():
            yield from asyncio.sleep(1)
            self.network_manager.set_mock_path(mock.pretend_url)
            self.assertEqual(certification_dialog.button_box.button(QDialogButtonBox.Ok).text(), "&Ok")
            QTest.mouseClick(certification_dialog.radio_pubkey, Qt.LeftButton)
            QTest.keyClicks(certification_dialog.edit_pubkey, "FADxcH5LmXGmGFgdixSes6nWnC4Vb4pRUBYT81zQRhjn")
            QTest.mouseClick(certification_dialog.button_box.button(QDialogButtonBox.Ok), Qt.LeftButton)

        self.lp.call_later(15, close_dialog)
        asyncio.async(exec_test())
        self.lp.run_until_complete(open_dialog(certification_dialog))


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr)
    logging.getLogger().setLevel(logging.DEBUG)
    unittest.main()
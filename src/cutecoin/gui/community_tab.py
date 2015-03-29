'''
Created on 2 févr. 2014

@author: inso
'''

import logging
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtWidgets import QWidget, QMessageBox, QAction, QMenu, QDialog, \
                            QAbstractItemView
from ..models.members import MembersFilterProxyModel, MembersTableModel
from ..gen_resources.community_tab_uic import Ui_CommunityTabWidget
from cutecoin.gui.contact import ConfigureContactDialog
from cutecoin.gui.member import MemberDialog
from .wot_tab import WotTabWidget
from .transfer import TransferMoneyDialog
from .password_asker import PasswordAskerDialog
from .certification import CertificationDialog
from ..tools.exceptions import PersonNotFoundError, NoPeerAvailable
from ..core.person import Person


class CommunityTabWidget(QWidget, Ui_CommunityTabWidget):

    '''
    classdocs
    '''

    def __init__(self, account, community, password_asker):
        '''
        Constructor
        '''
        super().__init__()
        logging.debug("Info")
        self.setupUi(self)
        self.community = community
        self.account = account
        self.password_asker = password_asker
        logging.debug("Table")
        members_model = MembersTableModel(community)
        logging.debug("Filter")
        proxy_members = MembersFilterProxyModel()
        proxy_members.setSourceModel(members_model)
        self.table_community_members.setModel(proxy_members)
        self.table_community_members.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_community_members.customContextMenuRequested.connect(self.member_context_menu)
        self.table_community_members.sortByColumn(0, Qt.AscendingOrder)

        if self.account.member_of(self.community):
            self.button_membership.setText("Renew membership")
        else:
            self.button_membership.setText("Send membership demand")
            self.button_leaving.hide()

        self.wot_tab = WotTabWidget(account, community, password_asker, self)
        self.tabs_information.addTab(self.wot_tab, QIcon(':/icons/wot_icon'), "WoT")

    def member_context_menu(self, point):
        index = self.table_community_members.indexAt(point)
        model = self.table_community_members.model()
        if index.row() < model.rowCount():
            source_index = model.mapToSource(index)
            pubkey_col = model.sourceModel().columns_ids.index('pubkey')
            pubkey_index = model.sourceModel().index(source_index.row(),
                                                   pubkey_col)
            pubkey = model.sourceModel().data(pubkey_index, Qt.DisplayRole)
            member = Person.lookup(pubkey, self.community)
            menu = QMenu(self)

            informations = QAction("Informations", self)
            informations.triggered.connect(self.menu_informations)
            informations.setData(member)

            add_contact = QAction("Add as contact", self)
            add_contact.triggered.connect(self.menu_add_as_contact)
            add_contact.setData(member)

            send_money = QAction("Send money", self)
            send_money.triggered.connect(self.menu_send_money)
            send_money.setData(member)

            certify = QAction("Certify identity", self)
            certify.triggered.connect(self.menu_certify_member)
            certify.setData(member)

            view_wot = QAction("View in WoT", self)
            view_wot.triggered.connect(self.view_wot)
            view_wot.setData(member)

            menu.addAction(informations)
            menu.addAction(add_contact)
            menu.addAction(send_money)
            menu.addAction(certify)
            menu.addAction(view_wot)

            # Show the context menu.
            menu.exec_(QCursor.pos())

    def menu_informations(self):
        person = self.sender().data()
        self.member_informations(person)

    def menu_add_as_contact(self):
        person = self.sender().data()
        self.add_member_as_contact(person)

    def menu_send_money(self):
        person = self.sender().data()
        self.send_money_to_member(person)

    def menu_certify_member(self):
        person = self.sender().data()
        self.certify_member(person)

    def member_informations(self, person):
        dialog = MemberDialog(self.account, self.community, person)
        dialog.exec_()

    def add_member_as_contact(self, person):
        dialog = ConfigureContactDialog(self.account, self.window(), person)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            self.window().refresh_contacts()

    def send_money_to_member(self, person):
        dialog = TransferMoneyDialog(self.account, self.password_asker)
        dialog.edit_pubkey.setText(person.pubkey)
        dialog.combo_community.setCurrentText(self.community.name)
        dialog.radio_pubkey.setChecked(True)
        if dialog.exec_() == QDialog.Accepted:
            currency_tab = self.window().currencies_tabwidget.currentWidget()
            currency_tab.table_history.model().invalidate()

    def certify_member(self, person):
        dialog = CertificationDialog(self.account, self.password_asker)
        dialog.combo_community.setCurrentText(self.community.name)
        dialog.edit_pubkey.setText(person.pubkey)
        dialog.radio_pubkey.setChecked(True)
        dialog.exec_()

    def view_wot(self):
        person = self.sender().data()
        index_wot_tab = self.tabs_information.indexOf(self.wot_tab)
        # redraw WoT with this member selected
        self.wot_tab.draw_graph(person.pubkey)
        # change page to WoT
        self.tabs_information.setCurrentIndex(index_wot_tab)

    def send_membership_demand(self):
        password = self.password_asker.exec_()
        if self.password_asker.result() == QDialog.Rejected:
            return

        try:
            self.account.send_membership(password, self.community, 'IN')
            QMessageBox.information(self, "Membership",
                                 "Success sending membership demand")
        except ValueError as e:
            QMessageBox.critical(self, "Join demand error",
                              str(e))
        except PersonNotFoundError as e:
            QMessageBox.critical(self, "Key not sent to community",
                              "Your key wasn't sent in the community. \
                              You can't request a membership.")
        except NoPeerAvailable as e:
            QMessageBox.critical(self, "Network error",
                                 "Couldn't connect to network : {0}".format(e),
                                 QMessageBox.Ok)
        except Exception as e:
            QMessageBox.critical(self, "Error",
                                 "{0}".format(e),
                                 QMessageBox.Ok)

    def send_membership_leaving(self):
        reply = QMessageBox.warning(self, "Warning",
                             """Are you sure ?
Sending a membership demand  cannot be canceled.
The process to join back the community later will have to be done again."""
.format(self.account.pubkey), QMessageBox.Ok | QMessageBox.Cancel)
        if reply == QMessageBox.Ok:
            password_asker = PasswordAskerDialog(self.app.current_account)
            password = password_asker.exec_()
            if password_asker.result() == QDialog.Rejected:
                return

            try:
                self.account.send_membership(password, self.community, 'OUT')
                QMessageBox.information(self, "Membership",
                                     "Success sending leaving demand")
            except ValueError as e:
                QMessageBox.critical(self, "Leaving demand error",
                                  e.message)
            except NoPeerAvailable as e:
                QMessageBox.critical(self, "Network error",
                                     "Couldn't connect to network : {0}".format(e),
                                     QMessageBox.Ok)
            except Exception as e:
                QMessageBox.critical(self, "Error",
                                     "{0}".format(e),
                                     QMessageBox.Ok)

    def refresh_person(self, pubkey):
        if self is None:
            logging.error("community_tab self is None in refresh_person. Watcher connected to a destroyed tab")
        else:
            index = self.table_community_members.model().sourceModel().person_index(pubkey)
            self.table_community_members.model().sourceModel().dataChanged.emit(index[0], index[1])

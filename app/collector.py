# -*- coding: utf-8 -*-

import os
import csv

from trello import TrelloClient
from app.Exceptions import CFSyncConfigException
import logging

import httplib2
import datetime
import arrow


logger = logging.getLogger(__name__)

class TrelloCollector(object):
    """
    Class representing all Trello information required to do the SysDesEng reporting.
    """

    def __init__(self, report_config, trello_secret):
        self.client = TrelloClient(api_key = trello_secret[':consumer_key'],
                                   api_secret = trello_secret[':consumer_secret'],
                                   token = trello_secret[':oauth_token'],
                                   token_secret = trello_secret[':oauth_token_secret'])

        #Extract report configuration parameters
        self.cf_source = report_config['cf_source'];

        self.target_boards = report_config['add_cf_to']
        # TODO: remove below
        #self.report_parameters = report_config[':output_metadata'];
        #gen_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        # self.load_config(trello_sources, self.content[':output_metadata'][':trello_sources'])

    def load_config(self, config_src, report_metadata):
        """ load all config data related to trello sources and structure them in the report_metadata"""
        for card_type in config_src.keys(): #card_type is project|assignment|epic
            for board_t in config_src[card_type].keys():
                board_id = config_src[card_type][board_t][':board_id']
                if not board_id in report_metadata: # initialize if the board wasn't present during the iterations over other card_type's
                    if not board_id in report_metadata[':boards']:
                        report_metadata[':boards'][board_id] = {};
                    report_metadata[':boards'][board_id][':board_id'] = config_src[card_type][board_t][':board_id'] #copy board id
                    report_metadata[':boards'][board_id][':board_name'] = board_t
                    if not ':lists' in report_metadata[':boards'][board_id]:
                        report_metadata[':boards'][board_id][':lists'] = []

                #iterate through all the lists and populate them
                for list_t in config_src[card_type][board_t][':lists'].keys():
                    logger.debug("Adding board %s, list %s to the report" % (config_src[card_type][board_t][':board_id'], config_src[card_type][board_t][':lists'][list_t]))
                    list_id = config_src[card_type][board_t][':lists'][list_t]
                    report_metadata[':lists'][list_id] = {};
                    report_metadata[':lists'][list_id][':list_id'] = list_id
                    report_metadata[':lists'][list_id][':completed'] = False;
                    report_metadata[':lists'][list_id][':card_type'] = card_type;
                    report_metadata[':lists'][list_id][':board_id'] = board_id
                    report_metadata[':boards'][board_id][':lists'].append(list_id)
                if ':done_lists' in config_src[card_type][board_t]:
                    for list_t in config_src[card_type][board_t][':done_lists'].keys():
                        logger.debug("Adding board %s, Done list %s to the report" % (config_src[card_type][board_t][':board_id'], config_src[card_type][board_t][':done_lists'][list_t]))
                        list_id = config_src[card_type][board_t][':done_lists'][list_t]
                        report_metadata[':lists'][list_id] = {};
                        report_metadata[':lists'][list_id][':list_id'] = list_id
                        report_metadata[':lists'][list_id][':completed'] = True;
                        report_metadata[':lists'][list_id][':card_type'] = card_type;
                        report_metadata[':lists'][list_id][':board_id'] = board_id
                        report_metadata[':boards'][board_id][':lists'].append(list_id)

    def list_boards(self):
        boards = self.client.list_boards(board_filter="open")
        for board in boards:
            for tlist in board.all_lists():
                logger.info('board name: %s is here, board ID is: %s; list %s is here, list ID is: %s' % (board.name, board.id, tlist.name, tlist.id)) 

    def list_cf(self):
        """
        list boards that contain custom field sources.
        :returns: list of dicts each corresonding to custom field card
        """
        if len(self.cf_source) <1:
            raise CFSyncConfigException("No boards with custom fields in the configuration file")
        cf_list = []
        for brd in self.cf_source:
            cf_val=dict(name=brd['cf_name'],
                        board_id=brd['board_id'])
            cf_val['values'] = self._list_cf_boards(brd['board_id'])
            cf_list.append(cf_val)
        return cf_list

    def _list_cf_boards(self, board_id):
        """
        Helper method that lists custom field cards within the board.
        :returns: list of dicts each corresonding to custom field card
        """
        # TODO: self.validate_lists_on_board()
        try:
            brd = self.client.get_board(board_id)
            cards = brd.open_cards()
        except e:
            # TODO
            logger.error("TODO!!")
        cf_list = []
        for card in cards:
            cf = dict(name=card.name,
                      list_id=card.idList)
            logger.debug("Adding card {0}".format(cf))
            cf_list.append(cf)
        return cf_list

    def get_cf_opts(self, board_id, cf_name):
        """
        get all custom fields and options from the target board
        """
        brd = self.client.get_board(board_id)
        for cf in brd.get_custom_fields():
            if cf.name == cf_name:
                logger.debug("Custom field cf {}".format(cf.options))
                if cf.type != 'list':
                    logger.error("Incorrect Custom Field type '{}', only 'list' is supported".format(cf.type))
                opt_list = []
                for opt in cf.options:
                    opt_list.append(opt.get('value').get('text'))
                return opt_list
        logger.info("Custom field {0} not present on board {1}".format(cf_name, board_id))

    def diff_cf_opts(self, board_id):
        cf_list = self.list_cf()
        logger.info("cf_list is {}".format(cf_list))
        for cf_val in cf_list:
            self._diff_cf_for_board(cf_val, board_id)

    def _diff_cf_for_board(self, cf_val, board_id):
        logger.info("Custom field name: {}".format(cf_val['name']))
        for cf in cf_val['values']:
            logger.info("CF values: {0}, status: {1}".format(cf['name'], cf['list_id']))
        logger.info("**** custom fields applied: ****")
        existing_cfs = self.get_cf_opts(board_id, cf_val['name'])
        logger.info("Applied custom fields: {0} for board: {1}".format(existing_cfs, board_id))
        opts_to_add = []


    def parse_trello(self, deep_scan):
        """
        :deep_scan: If deep_scan is True the scan will traverse actions, otherwise just a light scan(much faster)
        Main function to parse all Trello boards and lists.
        """
        trello_sources = self.content[':output_metadata'][':trello_sources'];
        logger.debug('The sources are %s' % (trello_sources))

        for board_id in trello_sources[':boards'].keys():
            tr_board = self.client.get_board(board_id);
            tr_board.fetch(); # get all board properties
            members = [ (m.id, m.full_name) for m in tr_board.get_members()];
            trello_sources[':boards'][board_id][':members'] = members;
            logger.info('----- querying board %s -----' % (trello_sources[':boards'][board_id][':board_name']))
            logger.debug('Board members are %s' % (trello_sources[':boards'][board_id][':members']))

            #trello_sources[board_id][':cards'] = []
            cards = tr_board.get_cards();

    
            for card in cards:
                card_content = {}
                card_content[':name'] = card.name
                card_content[':id'] = card.id
                card_content[':members'] = []
                card_content[':board_id'] = tr_board.id
                for member_id in card.member_ids:
                    for (m_id, m_full_name) in members:
                        if member_id == m_id :
                           card_content[':members'].append((m_id,m_full_name))
                card_content[':desc'] = card.desc
                card_content[':short_url'] = card.url
                card_content[':labels'] = [(label.name,label.color) for label in card.labels]
                #self.logger.debug('Card: {0} | LABELES are {1}'.format(card_content[':name'], card_content[':labels']))
                card_content[':board_name'] = tr_board.name
                card_content[':list_id'] = card.list_id
                if card.due:
                    card_content[':due_date'] = arrow.get(card.due).format('YYYY-MM-DD HH:mm:ss')
                trello_sources[':cards'].append(card_content);

            logger.debug('%s cards were collected' % (len(cards)))

            tr_board.fetch_actions(action_filter="commentCard,updateCard:idList,createCard,copyCard,moveCardToBoard,convertToCardFromCheckItem",action_limit=1000);
            trello_sources[':boards'][board_id][':actions'] = sorted(tr_board.actions,key=lambda act: act['date'], reverse=True)
            logger.debug('%s actions were collected' % (len(trello_sources[':boards'][board_id][':actions'])))
            #self.logger.debug('Oldest action is %s' % (trello_sources[':boards'][board_id][':actions'][-1]))

            tr_lists = tr_board.all_lists()
            for tr_list in tr_lists:
                if tr_list.id in trello_sources[':lists']:
                    trello_sources[':lists'][tr_list.id][':name'] = tr_list.name;
            logger.info('the lists are %s' % (tr_lists))

        return self.content


    def parse_card_details(self, card_id):
        card = card_details.CardDetails(card_id, self.client, self.content[':output_metadata'])
        details = card.fill_details();
        #self.logger.debug('Card\'s details are: %s' % (details))
        return details

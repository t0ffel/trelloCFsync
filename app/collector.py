# -*- coding: utf-8 -*-

from trello import TrelloClient
from app.Exceptions import CFSyncConfigException
import logging

logger = logging.getLogger(__name__)


class TrelloCollector(object):
    """
    Class representing initial Trello connection interface.
    """

    def __init__(self, report_config, trello_secret):
        self.client = TrelloClient(api_key=trello_secret[':consumer_key'],
                                   api_secret=
                                   trello_secret[':consumer_secret'],
                                   token=trello_secret[':oauth_token'],
                                   token_secret=
                                   trello_secret[':oauth_token_secret'])

        #Extract report configuration parameters
        self.cf_source = report_config['cf_source']

        self.target_boards = report_config['add_cf_to']

    def list_boards(self):
        boards = self.client.list_boards(board_filter="open")
        for board in boards:
            for tlist in board.all_lists():
                logger.info('board name: %s is here, board ID is: %s; '
                            'list %s is here, list ID is: %s' % (board.name,
                                                                 board.id,
                                                                 tlist.name,
                                                                 tlist.id))

    def list_cf(self):
        """
        list boards that contain custom field sources.
        :returns: list of dicts each corresonding to custom field card
        """
        if len(self.cf_source) < 1:
            raise CFSyncConfigException("No boards with custom fields"
                                        " in the configuration file")
        cf_list = []
        for brd in self.cf_source:
            cf_val = dict(name=brd['cf_name'],
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
        except Exception as e:
            # TODO
            logger.error("Unhandled exception listing board %s" % e.message)
        cf_list = []
        for card in cards:
#            cf = dict(name=card.name,
#                      list_id=card.idList)
            logger.debug("Adding card {0}".format(card.name))
            cf_list.append(card.name)
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
                    logger.error("Use 'list', Custom Field type "
                                 "'{}' not supported".format(cf.type))
                opt_list = []
                for opt in cf.options:
                    opt_list.append(opt.get('value').get('text'))
                return opt_list
        logger.info("Custom field {0} not present on board {1}"
                    .format(cf_name, board_id))
        self.add_full_cf(brd, cf_name)

    def diff_cf_opts(self, board_id):
        cf_list = self.list_cf()
        logger.info("cf_list is {}".format(cf_list))
        for cf_val in cf_list:
            self._diff_cf_for_board(cf_val, board_id)

    def _diff_cf_for_board(self, cf_val, board_id):
        logger.info("Custom field name: {}".format(cf_val['name']))
        for cf in cf_val['values']:
            logger.info("CF values: {0}, status: {1}"
                        .format(cf['name'], cf['list_id']))
        logger.info("**** custom fields applied: ****")
        existing_cfs = self.get_cf_opts(board_id, cf_val['name'])
        logger.info("Applied custom fields: {0} for board: {1}"
                    .format(existing_cfs, board_id))

    def target_board_generator(self):
        for board_id in self.target_boards:
            yield self.client.get_board(board_id)

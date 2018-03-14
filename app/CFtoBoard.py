# -*- coding: utf-8 -*-

import logging


logger = logging.getLogger(__name__)


class CFtoBoard(object):
    """
    Class representing application of custom fields of a list type to a board
    """

    def __init__(self, field_name, field_options, board):
        self.board = board
        self.name = field_name
        self.options = field_options

    def check_and_add_board_cf(self):
        """
        get all custom fields and options from the target board.
        :returns: function that updates custom field/its options
        """
        def add_custom_field():
            options = self.get_cf_options()
            logger.info("Adding New custom field '{0}' with options '{1}'"
                        .format(self.name, options))
            field = self.board.add_custom_field(self.name, "list",
                                                cf_options=options)
            return field

        def add_cf_options(cf_object, missing_opts):
            for opt in missing_opts:
                logger.info("Adding option {0} to custom field {1}"
                            .format(opt, self.name))
                cf_object.add_list_option(opt)

        for cf in self.board.get_custom_fields():
            if cf.name == self.name:
                logger.debug("Custom field cf {}".format(cf.options))
                if cf.type != 'list':
                    logger.error("Incorrect Custom Field type '{}', "
                                 "only 'list' is supported".format(cf.type))
                    return None
                for opt in cf.options:
                    txt = opt.get('value').get('text')
                    if txt in self.options:
                        self.options.remove(txt)
                add_cf_options(cf, self.options)
                return None
        logger.info("Custom field {0} not present on board {1}"
                    .format(self.name, self.board))
        add_custom_field()

    def get_cf_options(self):
        options = []
        for opt in self.options:
            val = {'color': 'none',
                   'value': {'text': opt}}
            options.append(val)
        return options

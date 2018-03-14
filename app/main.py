#!/usr/bin/env python3

from app.collector import TrelloCollector

import logging
import tempfile
import os
import yaml
import argparse

import httplib2
from apiclient import discovery

def main():
    logging_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=logging_format,
                        level=logging.INFO)

    logger = logging.getLogger(__name__)


    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='report config', default="config/cfsync.yml")
    parser.add_argument('--deep-scan', help='query each individual card', dest='deep_scan', action='store_true')
    parser.add_argument('--no-deep-scan', help='query each individual card', dest='deep_scan', action='store_false')
    parser.set_defaults(deep_scan=True);
    parser.add_argument('action', nargs='?', help='report to produce the report, list to output boards and lists', default="report")
    args = parser.parse_args();


    if os.path.isfile(args.config):
         with open(args.config, 'r') as stream:
             report_config = yaml.load(stream)
    else:
        logger.error('Invalid configuration file!')
        return;

    with open("secrets/trello_secret.yml", 'r') as stream:
        trello_secret_config = yaml.load(stream)

    collector = TrelloCollector(report_config, trello_secret_config)
    logger.info('Started querying of Trello {}'.format(collector))

    if args.action == 'list':
        collector.list_boards(); #output list of Trello boards and lists 
        return
    elif args.action == 'list_cf':
        cf_list = collector.list_cf()
        for cf_val in cf_list:
            logger.info("Custom field name: {}".format(cf_val['name']))
            for cf in cf_val['values']:
                logger.info("CF values: {0}, status: {1}".format(cf['name'], cf['list_id']))
            logger.info("**** custom fields applied: ****")
            existing_cfs = collector.get_cf_opts(report_config['add_cf_to'][0], cf_val['name'])
            logger.info("Applied custom fields: {}".format(existing_cfs))
    elif args.action == 'list_cf2':
        collector.diff_cf_opts(report_config['add_cf_to'][0])
    elif args.action == 'sync_cf':
        
        return;
    else:
        logger.error('Unrecognized actions %s' % (args.action))
        return;


if __name__ == '__main__':

    main()

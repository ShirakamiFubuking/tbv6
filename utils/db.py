import sqlite3
import logging

logger = logging.getLogger('Database')

exc_info = False


class Handler:
    __database_conn_pool = {}

    def __init__(self, name, none_stop=False, rollback_anytime=True):
        self.name = name
        self.conn = sqlite3.connect(self.name)
        self._none_stop = none_stop
        self.cursor = self.conn.cursor()
        logger.debug('Database cursor init created')
        self.__rollback_anytime = rollback_anytime
        self.__exit = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__exit = True
        self.cursor.close()
        if not exc_type:
            self.conn.commit()
            logger.debug('All command execute successful. Commit success.')
        elif isinstance(exc_type, sqlite3.Error):
            self.conn.rollback()
            logger.warning('Database error! Rollback.')
            logger.warning(exc_val)
            if exc_info:
                logger.warning(exc_tb)
        elif self.__rollback_anytime:
            logger.warning('Other error! Database will rollback.')
            logger.warning(exc_val)
            if exc_info:
                logger.warning(exc_tb)
            self.conn.rollback()
        else:
            logger.warning('Other error! Database will not rollback.')
            logger.warning(exc_val)
            if exc_info:
                logger.warning(exc_tb)
            self.conn.commit()
        self.conn.close()
        logger.debug('Connection closed.')
        return self._none_stop

    def __del__(self):
        if self.__exit:
            logger.debug('Datebase has been committed. Auto exit.')
            return
        self.cursor.close()
        self.conn.commit()
        self.conn.close()
        logger.debug('Commit. Auto exit.')
        self.__exit = True

    delete = __del__

    def commit(self):
        self.cursor.close()
        self.conn.commit()
        logger.info('Manual commit.')

    def rollback(self):
        self.cursor.close()
        self.conn.rollback()
        logger.info('Manual rollback.')

    def refresh(self):
        self.commit()
        self.cursor = self.conn.cursor()
        logger.info('Create a new cursor')

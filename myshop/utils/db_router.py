class MasterSlaveDBRouter:
    """数据库主从读写分离路由"""

    def db_for_read(self, model, **hints):
        """数据库读操作"""
        return "slave"

    def db_for_write(self, model, **hints):
        """数据库写操作"""
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """是否运行关联操作"""
        return True

import argparse
import os
import re
import threading
import time
import xlwt

DEBUG = False


class CreateExcel:
    """
    CreateUnittestExecl工具可一键生成单元测试文档，便于产品自动化交付项目

    :params filename: 存放单元测试日志文件的文件夹
    :params save_path: 生成excel表格的存放路径
    :params svn_path: 单元测试文件在H3C SVN上的存放路径

    """
    __version__ = "1.0"
    __author__ = "zhanghao KF9676"
    # 单元测试的是否新增, 默认YES
    ADD_UNIT = "YES"
    # 单元测试是否测试通过, 默认PASS
    UNITTEST_FLAG = "PASS"
    # 单元测试时间节点, 默认为当前日期
    UNITTEST_DATE = time.strftime('%Y/%m/%d', time.localtime())
    # 单元测试版本, 默认为V1.0
    UNITTEST_VERSION = "V1.0"
    instance = None
    # 申请RLock
    lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        # 如果类对象存在，跳过申请和释放锁的操作，节省资源
        if cls.instance:
            return cls.instance
        # add RLock
        with cls.lock:
            if cls.instance:
                return cls.instance
            cls.instance = object.__new__(cls)
            return cls.instance

    def __init__(self):
        self.parse_argument = argparse.ArgumentParser("Parameter-parser for create Execl by unittest files")
        self._add_arguments()
        self.filename = ""
        self.save_path = ""
        self.unittest_svn_path = ""
        self.add_unit = self.ADD_UNIT
        self.unittest_flag = self.UNITTEST_FLAG
        self.unittest_date = self.UNITTEST_DATE
        self.version = self.UNITTEST_VERSION
        self.cols = ["序号", "函数名称", "版本", "单元测试用例名称", "新增", "单元测试用例描述", "测试结论", "责任人", "测试日期", "单元测试路径"]
        self.result = []
        self.parse_unittest_arguments()

    def _add_arguments(self):
        self.parse_argument.add_argument("-f", "--files", help="存放单元源文件的路径", dest="source_path", required=True)
        self.parse_argument.add_argument("-t", "--target", help="存放单元源文件的路径", dest="target_path", required=True)
        self.parse_argument.add_argument("-s", "--svn", help="存放单元源文件的路径", dest="svn_path", required=True)

    def parse_unittest_arguments(self):
        unittest_args = self.parse_argument.parse_args()
        source_path = unittest_args.source_path
        target_path = unittest_args.target_path
        svn_path = unittest_args.svn_path
        if not all([source_path, target_path, svn_path]):
            return "缺少必要参数"
        self.filename = source_path
        self.save_path = r'{0}/unittest_{1}.xls'.format(target_path, time.strftime('%Y%m%d%H%M%S', time.localtime()))
        self.unittest_svn_path = svn_path
        # 获取单元测试关键信息写入execl中
        self.get_unittest_info()
        self.write_unittest_info()

    def get_file_list(self):
        file_list = os.listdir(self.filename)
        for index, file in enumerate(file_list):
            if ".robot" not in file:
                file_list.pop(index)
            if ".py" in file:
                file_list.pop(index)
        return file_list

    @staticmethod
    def read_file(file_name):
        file_dict = []
        with open(file_name, "r", encoding="utf-8") as f:
            file_list = f.readlines()
            test_case_index = 0
            keyword_case_index = 0
            author = ""
            for index, info in enumerate(file_list):
                if "Author" in info:
                    author = info.split("Author:")[1].split(", ")[0]
                if "*** Test Cases ***" in info:
                    test_case_index = index
                if "*** Keywords ***" in info:
                    keyword_case_index = index
            if not keyword_case_index:
                keyword_case_index = len(file_list)
            buffer = file_list[test_case_index + 1: keyword_case_index]
            for index, msg in enumerate(buffer):
                column = {}
                if re.search(r"^(\s)", msg):
                    continue
                for j in buffer[index::]:
                    if "[Documentation]" in j:
                        column["Documentation"] = j.replace("[Documentation]", "").strip()
                        break
                if "\\" in file_name:
                    file_name = file_name.split("\\")[1]
                column["test_result"] = "PASS"
                column["author"] = author.strip() or ""
                column["unittest"] = msg.strip() or ""
                file_dict.append(column)
        return file_dict

    def get_unittest_info(self):
        result = []
        file_list = self.get_file_list()
        for file in file_list:
            unit_test_path = self.filename + '\\' + file
            file_dict = self.read_file(unit_test_path)
            for i in file_dict:
                i["function_name"] = file.split(".")[0]
                result.append(i)
        self.result = result

    def write_unittest_info(self):
        book = xlwt.Workbook(encoding='utf-8', style_compression=0)
        sheet = book.add_sheet('单元测试', cell_overwrite_ok=True)
        for col in range(len(self.cols)):
            sheet.write(0, col, self.cols[col])
        for index, unit in enumerate(self.result):
            sheet.write(index + 1, 0, str(index + 1))  # 序号
            sheet.write(index + 1, 1, unit["function_name"])  # 函数名称
            sheet.write(index + 1, 2, self.version)  # 版本
            sheet.write(index + 1, 3, unit["unittest"])  # 单元测试用例名称
            sheet.write(index + 1, 4, self.add_unit)  # 新增
            sheet.write(index + 1, 5, unit["Documentation"])  # 单元测试用例描述
            sheet.write(index + 1, 6, self.unittest_flag)  # 测试结论
            sheet.write(index + 1, 7, unit["author"])  # 责任人
            sheet.write(index + 1, 8, self.unittest_date)  # 测试日期
            sheet.write(index + 1, 9, self.unittest_svn_path)  # 单元测试路径

        print("单元测试文件生成成功，路径为{}".format(self.save_path))
        book.save(self.save_path)


if __name__ == '__main__':
    CreateExcel()

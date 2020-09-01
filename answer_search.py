# 语句查询及组织回答
from py2neo import Graph

from lib.result import Result
from lib.chain import TranslationChain, QueryType
from lib.wrapper import iter_one_name, iter_cross_name


class AnswerSearcher:

    def __init__(self):
        self.graph = Graph('http://localhost:7474', auth=('neo4j', 'shawn'))

    def search(self, result: Result):
        for qt, chain in result.sqls.items():
            data = self._search_data(chain)
            answer = self.organize(qt, data, result)
            print(3, answer)
            print()

    def _search_data(self, chain: TranslationChain) -> list:
        data = []
        if chain.query_type == QueryType.Direct:
            data = self._search_direct(chain)
        elif chain.query_type == QueryType.DirectThenFeed:
            pass
        elif chain.query_type == QueryType.DoubleDirectThenFeed:
            pass
        print(2, data)
        return data

    def _search_direct(self, chain: TranslationChain) -> list:
        """ 进行直接查询 """
        results = []
        for sql in chain.iter():
            print(1, sql)
            result = self.graph.run(sql).data()
            results.append(result if result else None)
        return results

    def organize(self, qt: str, data: list, result: Result) -> str:
        answer = ''
        # 年度总体状况
        if qt == 'year_status':
            answer = f'{result["year"][0]}年，{data[0][0]["y.info"]}'
        # 年度目录状况
        elif qt == 'catalog_status':
            answer = iter_one_name(data, result['catalog'],
                                   ok_pattern=lambda x, n: f'{n}在{x[0]["r.info"]}',
                                   none_pattern=lambda n: f'并没有关于{n}的描述')
        # 年度目录包含哪些
        elif qt == 'exist_catalog':
            answer = '本年目录包括: ' + ', '.join([item['c.name'] for item in data[0]])
        # 指标值
        elif qt == 'index_value':
            answer = iter_one_name(data, result['index'],
                                   ok_pattern=lambda x, n: f'{n}: {x[0]["r.value"]}{x[0]["r.unit"]}',
                                   none_pattern=lambda n: f'{n}: 无数据记录')
        # 地区指标值
        elif qt == 'area_value':
            answer = iter_cross_name(data, result['area'], result['index'],
                                     ok_pattern=lambda x, m, n: f'{m}{x[0]["r.repr"]}{n}: {x[0]["r.value"]}{x[0]["r.unit"]}',
                                     none_pattern=lambda m, n: f'{m}{n}: 无数据记录')

        return answer

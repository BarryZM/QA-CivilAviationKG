# 语句查询及组织回答
from py2neo import Graph

from lib.wrapper import *
from lib.utils import sign
from lib.result import Result
from lib.chain import TranslationChain


class AnswerSearcher:

    def __init__(self):
        self.graph = Graph('http://localhost:7474', auth=('neo4j', 'shawn'))

    def search(self, result: Result):
        for qt, chain in result.sqls.items():
            answer = self.organize(qt, chain, result)
            print('[---]', answer)
            print()

    def _search_direct(self, sql_gen, offset: int = 0) -> list:
        """ 进行直接查询 """
        results = []
        if isinstance(sql_gen, TranslationChain):
            generator = sql_gen.iter(offset)
        else:
            generator = sql_gen
        for sql in generator:
            print(1, sql)
            if sql is None:
                results.append(None)
                continue
            result = self.graph.run(sql).data()
            results.append(result if result else None)
        return results

    def _search_double_direct_then_feed(self, chain: TranslationChain, unpack_key_name: str) -> tuple:
        """ 第一次直接查询，第二次先执行直接查询后将查询结果投递至最后的查询 """
        results_1 = self._search_direct(chain)
        temp_res = self._search_direct(chain, 1)
        sqls = []
        for feed in temp_res:
            for pattern_sql in chain.iter(2):
                if feed is None:
                    sqls.append(None)
                    continue
                sqls.append(pattern_sql.format(feed[0][unpack_key_name]))
        results_2 = self._search_direct(sqls)
        return results_1, results_2, temp_res

    def organize(self, qt: str, chain: TranslationChain, result: Result) -> str:
        answer = ''
        # 年度总体状况
        if qt == 'year_status':
            data = self._search_direct(chain)
            answer = f'{result["year"][0]}年，{data[0][0]["y.info"]}'
        # 年度目录状况
        elif qt == 'catalog_status':
            data = self._search_direct(chain)
            answer = iter_with_name(data, result['catalog'],
                                    ok_pattern=lambda x, n: f'{n}在{x[0]["r.info"]}',
                                    none_pattern=lambda n: f'并没有关于{n}的描述')
        # 年度目录包含哪些
        elif qt == 'exist_catalog':
            data = self._search_direct(chain)
            answer = '本年目录包括: ' + ', '.join([item['c.name'] for item in data[0]])
        # 指标值
        elif qt == 'index_value':
            data = self._search_direct(chain)
            answer = iter_with_name(data, result['index'],
                                    ok_pattern=lambda x, n: f'{n}: {x[0]["r.value"]}{x[0]["r.unit"]}',
                                    none_pattern=lambda n: f'{n}: 无数据记录')
        # 指标占总比
        elif qt == 'index_overall':
            data = self._search_double_direct_then_feed(chain, 'n.name')
            answer = iter_with_feed(data, result['index'],
                                    binary_cmp_and_patterns=[
                                        (None,
                                         lambda _, n, x, y, f: f'{n}: {x[0]["r.value"]}{x[0]["r.unit"]}'),
                                        (lambda x, y: float(x[0]['r.value']) / float(y[0]['r.value']),
                                         lambda r, n, x, y, f: f'其占总体（{f[0]["n.name"]}）的{r}'),
                                        (lambda x, y: float(y[0]['r.value']) / float(x[0]['r.value']),
                                         lambda r, n, x, y, f: f'总体（{f[0]["n.name"]}）是其的{r}倍')
                                    ],
                                    err_pattern=lambda n: f'无效的{n}值类型-无法比较',
                                    x_none_pattern=lambda n: f'无{n}的数据记录-无法比较',
                                    y_none_pattern=lambda n: f'无{n}的父级数据记录-无法比较',
                                    all_none_pattern=lambda _: '无任何数据记录-无法比较')
        # 指标倍数比较（只有两个指标）
        elif qt == 'indexes_m_compare':
            data = self._search_direct(chain)
            answer = iter_with_binary(data, result['index'],
                                      (None,
                                       lambda _, x, y, n1, n2: f'{n1}为{x[0]["r.value"]}{x[0]["r.unit"]}，{n2}为{y[0]["r.value"]}{y[0]["r.unit"]}'),
                                      (lambda x, y: float(x[0]['r.value']) / float(y[0]['r.value']),
                                       lambda r, x, y, n1, n2: f'前者是后者的{r}倍'),
                                      (lambda x, y: float(y[0]['r.value']) / float(x[0]['r.value']),
                                       lambda r, x, y, n1, n2: f'后者占前者的{r}'))
        # 指标数量比较（只有两个指标）
        elif qt == 'indexes_n_compare':
            data = self._search_direct(chain)
            answer = iter_with_binary(data, result['index'],
                                      (None,
                                       lambda _, x, y, n1, n2: f'{n1}为{x[0]["r.value"]}{x[0]["r.unit"]}，{n2}为{y[0]["r.value"]}{y[0]["r.unit"]}'),
                                      (lambda x, y: float(x[0]['r.value']) - float(y[0]['r.value']),
                                       lambda r, x, y, n1, n2: f'前者比后者{sign(r)}{abs(r)}{x[0]["r.unit"]}'))
        # 地区指标值
        elif qt == 'area_value':
            data = self._search_direct(chain)
            answer = iter_with_name(data, result['area'], result['index'],
                                    ok_pattern=lambda x, m, n: f'{m}{x[0]["r.repr"]}{n}: {x[0]["r.value"]}{x[0]["r.unit"]}',
                                    none_pattern=lambda m, n: f'{m}{n}: 无数据记录')
        # 地区指标占总比
        elif qt == 'area_overall':
            data = self._search_double_direct_then_feed(chain, 'n.name')
            answer = iter_with_feed(data, result['area'], result['index'],
                                    binary_cmp_and_patterns=[
                                        (None,
                                         lambda _, n1, n2, x, y, f: f'{n1}{x[0]["r.repr"]}的{n2}：{x[0]["r.value"]}{x[0]["r.unit"]}'),
                                        (lambda x, y: float(x[0]['r.value']) / float(y[0]['r.value']),
                                         lambda r, n1, n2, x, y, f: f'其占总体（{f[0]["n.name"]}{n2}）的{r}'),
                                        (lambda x, y: float(y[0]['r.value']) / float(x[0]['r.value']),
                                         lambda r, n1, n2, x, y, f: f'总体（{f[0]["n.name"]}{n2}）是其的{r}倍')
                                    ],
                                    err_pattern=lambda n1, n2: f'{n1}中无效的{n2}值类型-无法比较',
                                    x_none_pattern=lambda n1, n2: f'{n1}无{n2}的数据记录-无法比较',
                                    y_none_pattern=lambda n1, n2: f'{n1}无{n2}的父级数据记录-无法比较',
                                    all_none_pattern=lambda _: '无任何数据记录-无法比较')

        return answer

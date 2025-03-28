import pandas as pd
import pyecharts.options as opts
from pyecharts.charts import Line
from pyecharts.charts import Bar
import os
from typing import Dict, List
import sys

half_period = 360  #半衰期
point = 144

analyze_output = "./analyze_output"

stability_data = None


def project_fuzzer_score(datas: Dict[str, Dict[str, float]], page_title:str, filename:str) -> None:
    """ 给 项目和fuzzer 的分数绘图

    Args:
        datas (Dict[str, Dict[str, float]]): {项目：{fuzzer, score}, ...}
    """

    # 确定有多少项目和多少fuzzer
    projects = list(datas.keys())
    fuzzers = []
    for p in datas.keys():
        fuzzers.extend(list(datas[p].keys()))
    fuzzers = set(fuzzers)
    bar = Bar(init_opts=opts.InitOpts(width="1450px", height="1500px", bg_color="white", page_title=page_title, is_horizontal_center=True))
    # x轴数据
    bar.add_xaxis(projects)

    for f in fuzzers:
        values = []
        for t in projects:
            try:
                if datas[t][f] > 25:
                    values.append(opts.BarItem(name=f, value=datas[t][f], label_opts=opts.LabelOpts(formatter="{b} {c}")))
                else:
                    values.append(opts.BarItem(name=f, value=datas[t][f], label_opts=opts.LabelOpts(formatter="{b} {c}", position="right")))
            except KeyError as e:
                values.append(opts.BarItem(name=f, value=0, label_opts=opts.LabelOpts(formatter="{b} {c}", position="right")))
                print(f"{e} not exits")
        #sorted_values = sorted(values, key=lambda x: x.opts['value'], reverse=True)
        bar.add_yaxis(f, values)
    # 将x轴和y轴交换
    bar.reversal_axis()

    # 配置柱状图的样式
    bar.set_global_opts(
        title_opts=opts.TitleOpts(title=None, subtitle=None, pos_left="15%"),
        toolbox_opts=opts.ToolboxOpts(is_show=True),
        xaxis_opts=opts.AxisOpts(name="分数"),
        yaxis_opts=opts.AxisOpts(name="项目"),
    )
    bar.render(os.path.join(analyze_output, f"{filename}.html"))


def fuzzer_score(datas:Dict[str,float]) -> None:
    """ 给最终的 fuzzer 得分绘图

    Args:
        datas (Dict[str,float]): {{fuzzer:score}, ...}
    """

    fuzzers = list(datas.keys())
    values = list(datas.values())
    bar = Bar(init_opts=opts.InitOpts(width="1200px", height="876px", bg_color="white", page_title="开源FUZZ性能对比", is_horizontal_center=True))
    # x轴数据
    bar.add_xaxis(fuzzers)
    bar.add_yaxis("分数", values)

    # 配置柱状图的样式
    bar.set_global_opts(
        title_opts=opts.TitleOpts(title=None, subtitle=None, pos_left="15%"),
        xaxis_opts=opts.AxisOpts(name="FUZZ"),
        yaxis_opts=opts.AxisOpts(name="分数"),
    )

    bar.render('./analyze_output/汇总所有项目的fuzzer得分.html')


def weighted(values):
    """ 计算权值

    Args:
        values (_type_): _description_
    """
    weights = []
    for i in range(len(values)):
        w = 0.5 ** (i * 10 / 360)
        weights.append(w)
    return weights


def weighted_average(values):
    """
    计算加权平均值

    :param values: 数值列表
    :param weights: 权重列表，与数值列表一一对应
    :return: 加权平均值
    """
    weights = weighted(values)
    return sum(values[i] * weights[i] for i in range(len(values))) / sum(weights)


def time_averaging(datas):
    d = {}
    for k in datas.keys():
        d[k] = weighted_average(datas[k])
    return d


def global_end(datas):
    d = {}
    for k in datas.keys():
        d[k] = datas[k][-1]
    return d


def draw_line(datas, title, subtitle):
    line = Line(init_opts=opts.InitOpts(width="800px", height="400px", bg_color="white", page_title=f"开源FUZZ性能对比-{title}-{subtitle}"))
    line.add_xaxis(xaxis_data=list(range(point)))

    for k in datas.keys():
        line.add_yaxis(
            series_name=k,
            y_axis=datas[k],
            is_smooth=True
		)
    line.set_global_opts(
            title_opts=opts.TitleOpts(title=None, subtitle=None, pos_left="15%"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            toolbox_opts=opts.ToolboxOpts(is_show=True),
            xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
    )
    line.set_series_opts(label_opts=opts.LabelOpts(is_show=False))
    line.render(f"./analyze_output/{title}-{subtitle}.html")


def read_coverage(cov_path):
    df = pd.read_csv(cov_path, header=None, encoding="utf-8")
    new_df = pd.DataFrame({"fuzzer": df[1], "coverage": df[5] }, columns=["fuzzer", "coverage"])
    new_dict = dict()
    for k in list(set(new_df["fuzzer"])):
        data = new_df.loc[new_df["fuzzer"] == k]
        new_dict[k] = data["coverage"].to_list()[:point]

    return new_dict


def read_crashe(crashe_path):
    df = pd.read_csv(crashe_path, header=None, encoding="utf-8")
    new_df = pd.DataFrame({"fuzzer": df[1], "crashes": df[3]}, columns=["fuzzer", "crashes"])
    new_dict = dict()
    for k in list(set(new_df["fuzzer"])):
        data = new_df.loc[new_df["fuzzer"] == k]
        new_dict[k] = data["crashes"].to_list()[:point]

    return new_dict

def standard_scores(scores_datas):
    """ 计算出各个fuzzer的标准分

    Args:
        total_scores_datas (Dict[fuzzer, score]): fuzzer 在当前项目的总分

    Returns:
        Dict[fuzzer, score] : 标准分
    """
    new_dict = {}
    sort_d = sorted(scores_datas.items(), key=lambda x: x[1], reverse=True)
    max_v = sort_d[0][1] or 1
    for k, v in scores_datas.items():
        new_dict[k] = v / max_v * 100
    return new_dict


def total_scores(total_scores_datas):
    """ 计算出各个fuzzer在各项得分的总和

    Args:
        total_scores_datas (Dict[fuzzer, score]): fuzzer 在当前项目的总分

    Returns:
        Dict[fuzzer, score] : 标准分
    """
    new_dict = {}
    sort_d = sorted(total_scores_datas.items(), key=lambda x: x[1], reverse=True)
    max_v = sort_d[0][1] or 1
    for k, v in total_scores_datas.items():
        new_dict[k] = v / max_v * 100
    return new_dict


def read_stability_data(filename:str):
    """ 读取fuzzer稳定性数据

    Args:
        fn (str): filename
    """
    global stability_data
    stability_data = pd.read_csv(filename, header=0, encoding="utf-8")


def stability_scores(project_name:str, fuzzers:List[str]):
    """ 计算稳定性分数,总分为1,每次退出减0.1

    Args:
        project_name (str): 项目名称
        fuzzers (List[str]): fuzzzer 列表

    Returns:
        _type_: 稳定性分数
    """
    stability_scores_dict = {}
    for f in fuzzers:
        df = stability_data.loc[(stability_data["fuzzer"] == f) & (stability_data["project_name"] == project_name)]
        if df.shape[0] == 0:
            stability_scores_dict[f] = 100
        else:
            stability_scores_dict[f] = (1 - df["count"].iloc[0] / 10) * 100
    return stability_scores_dict


class Report(object):
    """ 统计准确性、性能、稳定性三项分数写入csv
    """
    def __init__(self, output_path):
        if not os.path.exists(output_path):
            print(f"Output path {output_path} not exists!")
            return None
        self.output_path = output_path
        self.accuracy_score = pd.DataFrame(columns=["项目",	"aflplusplus", "afl", "honggfuzz", "eclipser", "libfuzzer"])
        self.performance_score = pd.DataFrame(columns=["项目", "aflplusplus", "afl", "honggfuzz", "eclipser", "libfuzzer"])
        self.stability_score = pd.DataFrame(columns=["项目", "aflplusplus", "afl", "honggfuzz", "eclipser", "libfuzzer"])
        self.global_coverage = pd.DataFrame(columns=["项目", "aflplusplus", "afl", "honggfuzz", "eclipser", "libfuzzer"])
        self.global_detection_rate = pd.DataFrame(columns=["项目", "aflplusplus", "afl", "honggfuzz", "eclipser", "libfuzzer"])
        self.time_avg_coverage = pd.DataFrame(columns=["项目", "aflplusplus", "afl", "honggfuzz", "eclipser", "libfuzzer"])
        self.time_avg_detection_rate = pd.DataFrame(columns=["项目", "aflplusplus", "afl", "honggfuzz", "eclipser", "libfuzzer"])

    def write_accuracy(self, accuracy_score_dict):
        self.accuracy_score.loc[self.accuracy_score.shape[0]] = accuracy_score_dict

    def write_performance(self, performance_score_dict):
        self.performance_score.loc[self.performance_score.shape[0]] = performance_score_dict

    def write_stability(self, stability_score_dict):
        self.stability_score.loc[self.stability_score.shape[0]] = stability_score_dict

    def write2df(self, df, score_dict):
        df.loc[df.shape[0]] = score_dict

    def project_report(self, project, cov_values, crashe_values):
        file = open("./analyze_output/report.txt", mode="a+", encoding="utf-8")
        p_name = f"Project: {project}\n"
        file.write(p_name)
        total_score_dict = {}
        accuracy_dict = {}
        performance_dict = {}

        global_coverage_dict = {}
        global_detection_rate_dict = {}
        time_avg_coverage_dict = {}
        time_avg_detection_rate_dict = {}

        d = global_end(cov_values)
        sort_d = sorted(d.items(), key=lambda x: x[1], reverse=True)
        max_v = sort_d[0][1] or 1
        for key, value in d.items():
            file.write(f"\tfuzzer: {key}, global coverage: {value}\n")
            accuracy_dict[key] = value / max_v * 100 * 0.5
            global_coverage_dict[key] = value / max_v * 100

        d = global_end(crashe_values)
        sort_d = sorted(d.items(), key=lambda x: x[1], reverse=True)
        max_v = sort_d[0][1] or 1
        for key, value in d.items():
            file.write(f"\tfuzzer: {key}, global detection rate: {value}\n")
            accuracy_dict[key] += value / max_v * 100  * 0.5
            global_detection_rate_dict[key] = value / max_v * 100

        d = time_averaging(cov_values)
        sort_d = sorted(d.items(), key=lambda x: x[1], reverse=True)
        max_v = sort_d[0][1] or 1
        for key, value in d.items():
            file.write(f"\tfuzzer: {key}, time average coverage: {value}\n")
            performance_dict[key] = value / max_v * 100 * 0.5
            time_avg_coverage_dict[key] = value / max_v * 100

        d = time_averaging(crashe_values)
        sort_d = sorted(d.items(), key=lambda x: x[1], reverse=True)
        max_v = sort_d[0][1] or 1
        for key, value in d.items():
            file.write(f"\tfuzzer: {key}, time average detection rate: {value}\n")
            performance_dict[key] += value / max_v * 100 * 0.5
            time_avg_detection_rate_dict[key] = value / max_v * 100

        stability_score_dict = stability_scores(project, list(accuracy_dict.keys()))
        sort_d = sorted(stability_score_dict.items(), key=lambda x: x[1], reverse=True)
        stability_dict = {}
        max_v = sort_d[0][1] or 1
        for key, value in stability_score_dict.items():
            try:
                total_score_dict[key] += value / max_v * 100
                stability_dict[key] += value / max_v * 100
            except KeyError:
                total_score_dict[key] = value / max_v * 100
                stability_dict[key] = value / max_v * 100
            file.write(f"\tfuzzer: {key}, normal rate of stability: {value}\n")

        accuracy_dict = standard_scores(accuracy_dict)
        for k in accuracy_dict.keys():
            total_score_dict[k] += accuracy_dict[k]

        performance_dict = standard_scores(performance_dict)
        for k in performance_dict.keys():
            total_score_dict[k] += performance_dict[k]

        accuracy_dict["项目"] = project
        performance_dict["项目"] = project
        stability_score_dict["项目"] = project
        self.write_accuracy(accuracy_dict)
        self.write_performance(performance_dict)
        self.write_stability(stability_score_dict)

        global_coverage_dict["项目"] = project
        global_detection_rate_dict["项目"] = project
        time_avg_coverage_dict["项目"] = project
        time_avg_detection_rate_dict["项目"] = project
        self.write2df(self.global_coverage, global_coverage_dict)
        self.write2df(self.global_detection_rate, global_detection_rate_dict)
        self.write2df(self.time_avg_coverage, time_avg_coverage_dict)
        self.write2df(self.time_avg_detection_rate, time_avg_detection_rate_dict)


        scores = total_scores(total_score_dict)
        sort_d = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        for k, v in sort_d:
            file.write(f"\tfuzzer: {k}, score: {v}\n")

        file.write("--------------------------------------------\n\n")

        return scores

    def df2dict(self, df):
        result_dict = {}
        for p in df["项目"]:
            project_df = df.loc[df["项目"] == p]
            ser_dict = project_df.iloc[0].to_dict()
            del ser_dict["项目"]
            result_dict[p] = ser_dict
        return result_dict

    def draw_html(self, datas, page_title, filename):
        project_fuzzer_score(datas, page_title, filename)

    def write2disk(self):
        self.accuracy_score.to_csv(os.path.join(self.output_path, "准确性分数.csv"), index=None, encoding="utf-8")
        self.performance_score.to_csv(os.path.join(self.output_path, "性能分数.csv"), index=None, encoding="utf-8")
        self.stability_score.to_csv(os.path.join(self.output_path, "稳定性分数.csv"), index=None, encoding="utf-8")

        self.global_coverage.to_csv(os.path.join(self.output_path, "全局覆盖率分数.csv"), index=None, encoding="utf-8")
        self.global_detection_rate.to_csv(os.path.join(self.output_path, "全局检出率分数.csv"), index=None, encoding="utf-8")
        self.time_avg_coverage.to_csv(os.path.join(self.output_path, "时间平均覆盖率分数.csv"), index=None, encoding="utf-8")
        self.time_avg_detection_rate.to_csv(os.path.join(self.output_path, "时间平均检出率.csv"), index=None, encoding="utf-8")

        self.draw_html(self.df2dict(self.accuracy_score), "准确性分数", "准确性分数")
        self.draw_html(self.df2dict(self.performance_score), "性能分数", "性能分数")
        self.draw_html(self.df2dict(self.stability_score), "稳定性分数", "稳定性分数")


def run(coverage_dir:str, stablility_file:str) -> None:

    if not os.path.exists(coverage_dir):
        print(f"{coverage_dir} not exists!")
        return None
    if not os.path.exists(analyze_output):
        os.mkdir(analyze_output)

    read_stability_data(stablility_file)


    print(analyze_output)
    print(os.listdir(coverage_dir))

    report = Report(analyze_output)
    project_number = 0
    sum_score_dict = {}
    score_dict = {}
    fuzzer_count = {}
    for i in os.listdir(coverage_dir):
        project_number += 1
        project_dir = os.path.join(coverage_dir, i)
        coverage_file = os.path.join(project_dir, "coverage.txt")
        cov_values = read_coverage(coverage_file)
        draw_line(cov_values, i, "Coverage")
        crashe_file = os.path.join(project_dir, "crashe.txt")
        crashe_values = read_crashe(crashe_file)
        draw_line(crashe_values, i, "Crashes")
        score = report.project_report(i, cov_values, crashe_values)
        score_dict[i] = score
        for key, value in score.items():
            try:
                sum_score_dict[key] += value
                fuzzer_count[key] += 1
            except KeyError:
                sum_score_dict[key] = value
                fuzzer_count[key] = 1

    project_fuzzer_score(score_dict, "开源FUZZ性能对比", "每个项目各个Fuzzer的得分")

    # 最后的汇总
    file = open("./analyze_output/report.txt", mode="a+", encoding="utf-8")

    file.write("\n")
    file.write("--------------------------------------------\n")
    file.write("--------------FUZZER分数排名-----------------\n")
    file.write("--------------------------------------------\n")
    sorted_scores = {}
    for k, v in sum_score_dict.items():
        score = v / fuzzer_count[k]
        sorted_scores[k] = score
    sorted_values = sorted(sorted_scores.items(), key=lambda x: x[1], reverse=True)
    total_score_df = pd.DataFrame(columns=["项目", "平均分", "排名"])
    index = 1
    for k, score in sorted_values:
        file.write(f"\tfuzzer: {k}, score: {score}\n")
        total_score_df.loc[total_score_df.shape[0]] = [k, score, index]
        index += 1

    total_score_df.to_csv(os.path.join(analyze_output, "fuzzer排行.csv"), index=None, encoding="utf-8")
    file.write("--------------------------------------------\n\n")
    fuzzer_score(dict(sorted_values))
    report.write2disk()



def main():
    args = sys.argv
    if len(args) == 1:
        print("Please input coverage directory and stabilitly file.")
        return 0

    if len(args) == 3:
        coverage_path = args[1]
        stability_file = args[2]
        print(args)
        if not os.path.exists(coverage_path):
            print("Input coverage path not exists.")
            return 0

        if not os.path.exists(stability_file):
            print("Input stability file path not exists.")
            return 0

        run(coverage_path, stability_file)
    else:
        print("No extra parameters required.")
        return 0




if __name__ == "__main__":
    main()


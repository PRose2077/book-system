import requests
import json
from flask import current_app
from openai import OpenAI

def generate_content(normal_tags, tag_infos, writing_type):
    """
    调用DeepSeek AI生成内容
    :param normal_tags: 普通标签列表
    :param tag_infos: 带附加信息的标签列表 [{'tag': '标签名', 'info': '附加信息'}, ...]
    :param writing_type: 写作类型
    :return: 生成的内容
    """
    try:
        # https://api.deepseek.com  deepseek
        # https://dashscope.aliyuncs.com/compatible-mode/v1  阿里云百炼
        # https://api.siliconflow.cn/v1/chat/completions 硅基流动
        # 初始化DeepSeek客户端
        client = OpenAI(
            api_key="", # 你的deepseek api-kay
            base_url="https://api.deepseek.com",
        )
        # 
        # 根据写作类型选择对应的提示模板
        type_guidance = {
            'narrative': generate_narrative_prompt(normal_tags, tag_infos),
            'expository': generate_expository_prompt(normal_tags, tag_infos),
            'argumentative': generate_argumentative_prompt(normal_tags, tag_infos),
            'descriptive': generate_descriptive_prompt(normal_tags, tag_infos),
            'commentary': generate_commentary_prompt(normal_tags, tag_infos),
            'creative_poetry': generate_creative_poetry_prompt(normal_tags, tag_infos),
            'creative_novel': generate_creative_novel_prompt(normal_tags, tag_infos),
            'creative_script': generate_creative_script_prompt(normal_tags, tag_infos)
        }

        # 获取对应写作类型的提示语
        prompt = type_guidance.get(writing_type)
        if not prompt:
            raise ValueError(f"不支持的写作类型：{writing_type}")
        
        # 调用DeepSeek API
        current_app.logger.info(f"正在调用DeepSeek API生成内容")
        current_app.logger.info(f"普通标签：{normal_tags}")
        current_app.logger.info(f"带附加信息的标签：{tag_infos}")
        current_app.logger.info(f"写作类型：{writing_type}")

        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的写作助手"},
                {"role": "user", "content": prompt}
            ],
            stream=False
        )
        #非流式
        generated_text = response.choices[0].message.content
        current_app.logger.info("内容生成成功")
        return generated_text
        
    except Exception as e:
        error_msg = f"生成内容时发生错误：{str(e)}"
        current_app.logger.error(error_msg)
        return f"生成失败：{error_msg}"



def generate_narrative_prompt(normal_tags, tag_infos):
    """生成叙述文写作提示"""
    # 获取所有附加信息作为叙述主题
    narrative_subjects = []
    if tag_infos:
        for tag_info in tag_infos:
            narrative_subjects.append(f"{tag_info['tag']}：{tag_info['info']}")
    
    # 如果没有附加信息，使用普通标签或默认值
    if not narrative_subjects:
        if normal_tags and len(normal_tags) > 0:
            narrative_subjects = [f"关于{normal_tags[0]}的故事"]  # 使用第一个标签构造主题
        else:
            narrative_subjects = ["小爱同学"]  # 当没有任何标签时的默认值

    # 将所有主题组合成一个字符串
    narrative_subject = "、".join(narrative_subjects)

    tags_str = ', '.join([f'`{tag}`' for tag in normal_tags])

    
    return f"""请基于以下框架，生成一篇关于{narrative_subject}的记叙文写作指导：

        # 一、写作准备
        1. 标签分析与组合
           - 已有标签：{tags_str}
           - 这些标签能产生哪些有趣的组合？
           - 每个标签组合可能引发的故事情节是什么？
           - 哪些组合最适合表达{narrative_subject}的主题？

        2. 确定写作目的
           - 基于选定的标签组合，想要传达什么主题？
           - 读者阅读后应该获得什么感悟？
           - 如何让标签自然地融入故事发展？

        3. 分析目标读者
           - 读者对{narrative_subject}的了解程度如何？
           - 如何引起他们的阅读兴趣？
           - 需要补充哪些背景信息？

        # 二、内容规划
        1. 基于标签的故事要素设计
           A. 故事情节构思：
              - 核心事件规划：
                * 以{narrative_subject}为主线，如何将标签{tags_str}编织成完整故事？
                * 每个标签可以对应哪些具体事件或场景？
                * 这些事件之间的因果关系是什么？
              
              - 情节发展脉络：
                * 引子：选择哪些标签作为故事的切入点？
                * 发展：如何让不同标签之间产生联系，推动情节发展？
                * 高潮：哪些标签组合可以制造戏剧性冲突？
                * 结局：如何通过标签的巧妙运用化解矛盾？
              
              - 矛盾冲突设计：
                * 主要矛盾：哪些标签之间的碰撞最能体现主题？
                * 次要矛盾：其他标签如何创造辅助性的冲突？
                * 内心冲突：如何通过标签展现人物的心理斗争？

           B. 人物设定：
              - 主要人物：哪些标签最适合塑造主角形象？
              - 配角：其他标签如何转化为配角特征？
              - 人物关系：标签之间的关系如何体现在人物互动中？

           C. 场景设置：
              - 关键场景：每个重要标签需要什么样的场景来承载？
              - 场景转换：如何利用标签实现场景的自然过渡？
              - 环境氛围：通过哪些标签营造特定的场景氛围？

        2. 基于标签的内容组织
           A. 开头部分（选择以下一种开头方式）：
              - 环境式开头：用哪些标签描绘开篇场景？
              - 人物式开头：用哪些标签刻画人物特征？
              - 事件式开头：用哪些标签引发故事契机？
              - 悬念式开头：用哪些标签制造疑问？

           B. 主体部分（故事情节推进）：
              第一个场景：
              - 选用标签：[具体标签组合]
              - 情节安排：[对应事件]
              - 过渡方式：[如何自然引入下一组标签]

              第二个场景：
              - 选用标签：[具体标签组合]
              - 情节安排：[对应事件]
              - 矛盾铺垫：[如何制造冲突]

              核心场景：
              - 选用标签：[最重要的标签组合]
              - 情节安排：[关键事件]
              - 高潮设计：[如何推向高潮]

           C. 结尾部分：
              - 选用标签：[收尾的标签组合]
              - 情节安排：[结局设计]
              - 首尾呼应：[如何与开头标签形成对应]

        # 三、写作方法
        1. 叙述方法建议
           - 根据标签特点选择合适的叙述顺序
           - 选择最能展现标签效果的叙述视角
           - 围绕标签设计细节描写

        2. 语言运用建议
           - 如何用对话展现标签特征？
           - 结合标签进行五感描写
           - 选择适合标签的修辞手法

        3. 情感表达建议
           - 通过标签传递情感
           - 利用标签营造氛围
           - 用标签引发读者共鸣
        """


def generate_expository_prompt(normal_tags, tag_infos):
    """生成说明文写作提示"""
    # 获取所有附加信息作为说明主题
    expository_subjects = []
    if tag_infos:
        for tag_info in tag_infos:
            expository_subjects.append(f"{tag_info['tag']}：{tag_info['info']}")
    
    # 如果没有附加信息，使用普通标签或默认值
    if not expository_subjects:
        if normal_tags and len(normal_tags) > 0:
            expository_subjects = [f"关于{normal_tags[0]}的说明"]  # 使用第一个标签构造主题
        else:
            expository_subjects = ["小爱同学"]  # 当没有任何标签时的默认值

    # 将所有主题组合成一个字符串
    expository_subject = "、".join(expository_subjects)

    tags_str = ', '.join([f'`{tag}`' for tag in normal_tags])
    
    return f"""请基于以下框架，生成一篇关于{expository_subject}的说明文写作指导：

        # 一、写作准备
        1. 确定写作目的
           - 你想让读者了解{expository_subject}的哪些方面？
           - 读者阅读后应该获得什么知识或能力？
           - 如何运用标签{tags_str}来实现这个目的？

        2. 分析目标读者
           - 读者的知识背景如何？
           - 他们对{expository_subject}的认知程度如何？
           - 他们最关心哪些问题？

        # 二、内容规划
        1. 核心内容选择（根据写作目的选择合适的角度）
           - 概念类：本质特征、类型分类、基本原理
           - 过程类：操作步骤、使用方法、注意事项
           - 特征类：功能特点、优势价值、应用场景

        2. 内容组织方式
           A. 开头部分：
              - 如何引起读者兴趣？
                * 可以从标签{tags_str}中选择最吸引人的角度切入
                * 例如：[举出2-3个标签组合的具体运用方式]
              - 如何说明{expository_subject}的重要性？
                * 结合标签{tags_str}说明其价值和意义
                * 例如：[举出2-3个标签组合的具体运用方式]
              - 如何概述文章主要内容？
                * 用标签{tags_str}搭建内容框架
                * 例如：[举出2-3个标签组合的具体运用方式]

           B. 主体部分：
              - 核心内容分几个方面？
                * 可以根据标签{tags_str}的特点进行分类
                * 例如：[举出2-3个标签组合的具体分类方式]
              - 各部分之间如何过渡？
                * 利用标签{tags_str}之间的关联性建立连接
                * 例如：[举出2-3个标签之间的过渡示例]
              - 重点和难点如何突出？
                * 通过标签{tags_str}的重要程度来凸显
                * 例如：[举出2-3个标签强调重点的方式]

           C. 结尾部分：
              - 如何总结主要内容？
                * 回顾标签{tags_str}的核心要点
                * 例如：[举出2-3个标签总结的方式]
              - 如何升华主题？
                * 从标签{tags_str}中提炼深层意义
                * 例如：[举出2-3个标签升华主题的方式]
              - 如何引发思考？
                * 基于标签{tags_str}提出开放性问题
                * 例如：[举出2-3个标签引发思考的方式]

        # 三、写作方法
        1. 说明方法建议
           - 下定义：如何准确界定{expository_subject}？
           - 作比较：用什么来类比{expository_subject}？
           - 举例子：选择什么例子最有说服力？
           - 列数据：需要哪些数据支撑？

        2. 语言运用建议
           - 用词：准确性和通俗性如何平衡？
           - 句式：如何保持简洁清晰？
           - 段落：如何做到层次分明？

        3. 图文配合建议
           - 需要哪些示意图？
           - 图表应该放在哪里？
           - 如何让图文相得益彰？

        # 四、标签运用策略
        1. 如何运用已有标签（{tags_str}）：
           - 每个标签可以在哪些部分使用？
           - 标签之间如何组合？
           - 如何让标签自然融入文章？
        """
def generate_argumentative_prompt(normal_tags, tag_infos):
    """生成议论文写作提示"""
    # 获取所有附加信息作为议论主题
    argument_subjects = []
    if tag_infos:
        for tag_info in tag_infos:
            argument_subjects.append(f"{tag_info['tag']}：{tag_info['info']}")
    
    # 如果没有附加信息，使用普通标签或默认值
    if not argument_subjects:
        if normal_tags and len(normal_tags) > 0:
            argument_subjects = [f"关于{normal_tags[0]}的思考"]  # 使用第一个标签构造议题
        else:
            argument_subjects = ["小爱同学会不会统治世界"]  # 当没有任何标签时的默认值

    # 将所有主题组合成一个字符串
    argument_subject = "、".join(argument_subjects)

    tags_str = ', '.join([f'`{tag}`' for tag in normal_tags])

    # 判断是否有议论主题（通过检查tag_infos中是否包含info）
    has_argument_topic = any(tag_info.get('info') for tag_info in tag_infos)
    
    # 根据是否有议论主题生成不同的提示
    if has_argument_topic:
        # 如果是议论主题,生成论点建议和论证思路
        return f"""请基于以下框架，生成一篇关于{argument_subject}的议论文写作指导：

        # 一、写作准备
        1. 论题分析
           - {argument_subject}涉及哪些核心问题？
           - 这个主题有哪些可能的切入角度？
           - 结合标签{tags_str}可以展开哪些论述？

        2. 建议论点方向
           A. 可能的论点角度：
              - [根据标签组合生成3-5个可能的论点]
              - 每个论点的优劣分析
              - 如何选择最适合的论点

           B. 论点确立建议：
              - 如何让论点更有说服力？
              - 如何体现思想深度？
              - 如何保持创新性？

        # 二、内容规划
        1. 论证框架设计
           A. 论证方法建议：
              - 哪种论证方法最适合选定的论点？
              - 如何将不同论证方法结合使用？
              - 如何避免论证的薄弱环节？

           B. 论据准备：
              - 如何选择最有力的论据类型？
              - 每个标签可以转化为什么类型的论据？
              - 如何确保论据的可靠性？

        2. 内容组织
           A. 开头部分：
              - 如何从标签中选择合适的引题方式？
                * 可以从标签{tags_str}中选择最具争议性或话题性的角度
                * 例如：[举出2-3个标签组合的引题方式]
              - 如何自然引出论点？
                * 通过标签{tags_str}之间的关联引发思考
                * 例如：[举出2-3个标签组合的过渡方式]
              - 如何预示文章的论证思路？
                * 用标签{tags_str}搭建论证框架
                * 例如：[举出2-3个标签组合的框架示例]

           B. 主体部分：
              第一个论证层面：
              - 如何设计分论点？
                * 从标签{tags_str}中提取核心观点
                * 例如：[举出2-3个标签转化为分论点的示例]
              - 选用哪些标签作为论据？
                * 根据标签{tags_str}的特点选择合适的论据类型
                * 例如：[举出2-3个标签转化为论据的示例]
              - 采用什么论证方法？
                * 结合标签{tags_str}的性质选择论证方法
                * 例如：[举出2-3个标签对应的论证方法]

              第二个论证层面：
              - 如何与第一层面形成递进？
                * 利用标签{tags_str}之间的层次关系
                * 例如：[举出2-3个标签递进关系的示例]
              - 如何选择补充论据？
                * 深入挖掘标签{tags_str}的延伸意义
                * 例如：[举出2-3个标签延伸论据的示例]
              - 如何加强论证力度？
                * 通过标签{tags_str}的组合增强说服力
                * 例如：[举出2-3个标签组合增强论证的示例]

              第三个论证层面：
              - 如何推向论证高潮？
                * 整合标签{tags_str}的核心价值
                * 例如：[举出2-3个标签整合的示例]
              - 如何处理反方观点？
                * 利用标签{tags_str}应对可能的质疑
                * 例如：[举出2-3个标签处理反驳的示例]
              - 如何形成压倒性论证？
                * 通过标签{tags_str}的综合运用达到论证高潮
                * 例如：[举出2-3个标签综合论证的示例]

           C. 结尾部分：
              - 如何总结论证过程？
                * 回顾标签{tags_str}的论证脉络
                * 例如：[举出2-3个标签总结的示例]
              - 如何升华主题？
                * 从标签{tags_str}中提炼普遍意义
                * 例如：[举出2-3个标签升华的示例]
              - 如何展望未来？
                * 基于标签{tags_str}提出展望和建议
                * 例如：[举出2-3个标签展望的示例]

        # 三、写作技巧
        1. 论证技巧
           - 如何使论证更有说服力？
           - 如何处理反方观点？
           - 如何避免论证漏洞？

        2. 语言运用
           - 如何保持语言严谨性？
           - 如何增强表达力度？
           - 如何做到简洁有力？

        # 四、标签运用策略
        1. 标签{tags_str}的运用建议：
           - 每个标签可以作为什么类型的论据？
           - 标签之间如何组合论证？
           - 如何让标签自然融入论述？
        """
    else:
        # 如果是具体论点,直接生成论证思路
        return f"""请基于以下框架，生成一篇论证{argument_subject}的议论文写作指导：

        # 一、写作准备
        1. 论点分析
           - {argument_subject}的核心含义是什么？
           - 为什么要论证这个观点？
           - 可能遇到哪些反驳？

        2. 确定论证策略
           - 哪些标签适合作为论据？
           - 如何组织论证过程？
           - 需要预设哪些前提？

        # 二、内容规划
        1. 论证框架设计
           A. 论证方法选择：
              - 演绎论证：从一般到特殊
              - 归纳论证：从特殊到一般
              - 类比论证：通过相似性论证
              - 因果论证：建立因果关系

           B. 论据准备：
              - 事实论据：相关的客观事实
              - 理论论据：权威观点和理论
              - 例证论据：典型事例
              - 数据论据：统计数据支持

        2. 内容组织
           A. 开头部分：
              - 如何引出论题？
              - 如何明确立场？
              - 如何吸引读者？

           B. 主体部分：
              第一个论证层面：
              - 分论点设计
              - 论据选择
              - 论证方法

              第二个论证层面：
              - 分论点设计
              - 论据选择
              - 论证方法

              第三个论证层面：
              - 分论点设计
              - 论据选择
              - 论证方法

           C. 结尾部分：
              - 如何总结论证过程？
              - 如何升华主题？
              - 如何展望未来？

        # 三、写作技巧
        1. 论证技巧
           - 如何使论证更有说服力？
           - 如何处理反方观点？
           - 如何避免论证漏洞？

        2. 语言运用
           - 如何保持语言严谨性？
           - 如何增强表达力度？
           - 如何做到简洁有力？

        # 四、标签运用策略
        1. 标签{tags_str}的运用建议：
           - 每个标签可以作为什么类型的论据？
           - 标签之间如何组合论证？
           - 如何让标签自然融入论述？

        """
def generate_descriptive_prompt(normal_tags, tag_infos):
    """生成描写文写作提示"""
    # 获取所有附加信息作为描写对象
    descriptive_subjects = []
    if tag_infos:
        for tag_info in tag_infos:
            descriptive_subjects.append(f"{tag_info['tag']}：{tag_info['info']}")
    
    # 如果没有附加信息，使用普通标签或默认值
    if not descriptive_subjects:
        if normal_tags and len(normal_tags) > 0:
            descriptive_subjects = [normal_tags[0]]  # 使用第一个标签作为描写对象
        else:
            descriptive_subjects = ["小爱同学"]  # 当没有任何标签时的默认值

    # 将所有主题组合成一个字符串
    descriptive_subject = "、".join(descriptive_subjects)

    tags_str = ', '.join([f'`{tag}`' for tag in normal_tags])
    
    return f"""请基于以下框架，生成一篇关于{descriptive_subject}的描写文写作指导：

        # 一、写作准备
        1. 观察对象分析
           - {descriptive_subject}的基本特征是什么？
           - 它有哪些独特之处？
           - 如何将标签{tags_str}与描写对象关联？

        2. 分析目标读者
           - 读者对{descriptive_subject}的了解程度如何？
           - 需要补充哪些背景信息？
           - 如何引起读者的阅读兴趣？

        # 二、内容规划
        1. 整体结构设计
           A. 开头部分：
              - 如何选择最佳切入点？
                * 从标签{tags_str}中选择最具特色的元素
                * 例如：[举出2-3个标签作为开头的具体示例]
              - 如何自然引出描写对象？
                * 利用标签{tags_str}创造引人入胜的开场
                * 例如：[举出2-3个标签组合的开场方式]
              - 如何确立描写基调？
                * 通过标签{tags_str}营造整体氛围
                * 例如：[举出2-3个标签设置基调的方式]
              
           B. 主体部分：
              - 如何划分描写层次？
                * 根据标签{tags_str}的特点进行层次划分
                * 例如：[举出2-3个标签的层次划分方式]
              - 如何安排描写顺序？
                * 基于标签{tags_str}设计合理的描写顺序
                * 例如：[举出2-3个标签的描写顺序安排]
              - 如何过渡衔接？
                * 利用标签{tags_str}之间的关联实现自然过渡
                * 例如：[举出2-3个标签间的过渡方式]
              
           C. 结尾部分：
              - 如何总结特征？
                * 通过标签{tags_str}凝练核心特征
                * 例如：[举出2-3个标签总结的方式]
              - 如何升华主题？
                * 从标签{tags_str}中提炼深层含义
                * 例如：[举出2-3个标签升华的方式]
              - 如何给读者留下思考空间？
                * 基于标签{tags_str}设置开放性思考
                * 例如：[举出2-3个标签引发思考的方式]

        2. 感知体验设计
           A. 视觉感受：
              - 形状、大小、颜色
                * 用标签{tags_str}描绘外观特征
                * 例如：[举出2-3个标签的视觉描写示例]
              - 动态特征
                * 通过标签{tags_str}展现动态美
                * 例如：[举出2-3个标签的动态描写示例]
              - 光影变化
                * 结合标签{tags_str}描绘光影效果
                * 例如：[举出2-3个标签的光影描写示例]
           
           B. 听觉感受：
              - 自身声音
                * 运用标签{tags_str}描写声音特点
                * 例如：[举出2-3个标签的声音描写示例]
              - 环境声响
                * 通过标签{tags_str}营造声音环境
                * 例如：[举出2-3个标签的环境声音示例]
              - 声音变化
                * 利用标签{tags_str}展现声音变化
                * 例如：[举出2-3个标签的声音变化示例]
           
           C. 触觉感受：
              - 质地、温度
                * 用标签{tags_str}描写触感特征
                * 例如：[举出2-3个标签的触感描写示例]
              - 触摸感觉
                * 通过标签{tags_str}传达触觉体验
                * 例如：[举出2-3个标签的触觉描写示例]
           
           D. 嗅觉感受：
              - 固有气味
                * 运用标签{tags_str}描写特有气味
                * 例如：[举出2-3个标签的气味描写示例]
              - 环境香气
                * 结合标签{tags_str}营造气味环境
                * 例如：[举出2-3个标签的环境气味示例]
           
           E. 味觉感受（如适用）：
              - 味道特点
                * 用标签{tags_str}描绘味觉特征
                * 例如：[举出2-3个标签的味觉描写示例]
              - 味觉层次
                * 通过标签{tags_str}展现味觉层次
                * 例如：[举出2-3个标签的味觉层次示例]

        3. 段落组织方式
           A. 段落之间的关系：
              - 时间顺序
                * 利用标签{tags_str}构建时间线索
                * 例如：[举出2-3个标签的时序安排示例]
              - 空间顺序
                * 通过标签{tags_str}规划空间布局
                * 例如：[举出2-3个标签的空间安排示例]
              - 逻辑关系
                * 运用标签{tags_str}建立逻辑联系
                * 例如：[举出2-3个标签的逻辑关联示例]
           
           B. 段落内部结构：
              - 中心句设置
                * 用标签{tags_str}凝练段落主旨
                * 例如：[举出2-3个标签的中心句示例]
              - 细节展开
                * 通过标签{tags_str}展开具体细节
                * 例如：[举出2-3个标签的细节展开示例]
              - 照应呼应
                * 利用标签{tags_str}实现段落呼应
                * 例如：[举出2-3个标签的呼应方式示例]

        # 三、写作方法
        1. 描写方法运用
           - 如何运用多感官描写？
           - 如何进行对比描写？
           - 如何实现动静结合？
           - 如何做到虚实相生？

        2. 语言表达技巧
           - 修辞手法选择
           - 词语搭配创新
           - 句式变化运用
           - 意象塑造方法

        # 四、标签运用策略
        1. 如何运用已有标签（{tags_str}）：
           - 每个标签可以描写哪些方面？
           - 标签之间如何组合描写？
           - 如何让标签自然融入描写？
           - 如何通过标签突出特征？
        """   

def generate_commentary_prompt(normal_tags, tag_infos):
    """生成评论文写作提示"""
    # 获取所有附加信息作为评论对象
    commentary_subjects = []
    if tag_infos:
        for tag_info in tag_infos:
            commentary_subjects.append(f"{tag_info['tag']}：{tag_info['info']}")
    
    # 如果没有附加信息，使用普通标签或默认值
    if not commentary_subjects:
        if normal_tags and len(normal_tags) > 0:
            commentary_subjects = [f"关于{normal_tags[0]}的评论"]  # 使用第一个标签构造评论对象
        else:
            commentary_subjects = ["小爱同学"]  # 当没有任何标签时的默认值

    # 将所有主题组合成一个字符串
    commentary_subject = "、".join(commentary_subjects)

    tags_str = ', '.join([f'`{tag}`' for tag in normal_tags])
    
    return f"""请基于以下框架，生成一篇关于{commentary_subject}的评论文写作指导：

        # 一、写作准备
        1. 评论对象分析
           - {commentary_subject}的基本情况是什么？
           - 它在所属领域的地位如何？
           - 目前存在哪些主要评价？
           - 如何将标签{tags_str}与评论主题关联？

        2. 评论角度确定
           - 选择哪些方面进行评价？
           - 如何保持客观公正？
           - 如何体现个人见解？
           - 如何避免主观武断？

        # 二、内容规划
        1. 整体框架设计
           A. 开头部分：
              - 如何介绍评论对象？
                * 从标签{tags_str}中选择最具特色的角度切入
                * 例如：[举出2-3个标签组合的介绍方式]
              - 如何引出评论视角？
                * 基于标签{tags_str}确立评论立场
                * 例如：[举出2-3个标签组合的视角设定]
              - 如何提出核心观点？
                * 通过标签{tags_str}凝练中心论点
                * 例如：[举出2-3个标签组合的观点呈现]

           B. 主体部分：
              第一个评论层面：
              - 评价要点
                * 从标签{tags_str}中提炼关键评价点
                * 例如：[举出2-3个标签转化为评价要点]
              - 论据支持
                * 利用标签{tags_str}构建有力论据
                * 例如：[举出2-3个标签作为论据的示例]
              - 分析过程
                * 通过标签{tags_str}展开深入分析
                * 例如：[举出2-3个标签的分析方法]

              第二个评论层面：
              - 评价要点
                * 挖掘标签{tags_str}的延伸价值
                * 例如：[举出2-3个标签的延伸评价]
              - 论据支持
                * 组合标签{tags_str}形成新的论据
                * 例如：[举出2-3个标签组合的论据示例]
              - 分析过程
                * 运用标签{tags_str}进行多维度分析
                * 例如：[举出2-3个标签的分析角度]

              第三个评论层面：
              - 评价要点
                * 整合标签{tags_str}的核心价值
                * 例如：[举出2-3个标签的价值提炼]
              - 论据支持
                * 综合标签{tags_str}形成终极论据
                * 例如：[举出2-3个标签的综合论证]
              - 分析过程
                * 通过标签{tags_str}达到评价高潮
                * 例如：[举出2-3个标签的升华分析]

           C. 结尾部分：
              - 如何总结评价？
                * 回顾标签{tags_str}的评价要点
                * 例如：[举出2-3个标签的总结方式]
              - 如何提出建议？
                * 基于标签{tags_str}提出改进方向
                * 例如：[举出2-3个标签的建议形式]
              - 如何展望未来？
                * 利用标签{tags_str}展望发展前景
                * 例如：[举出2-3个标签的展望角度]

        2. 评论内容设计
           A. 事实依据：
              - 客观数据
                * 选择与标签{tags_str}相关的数据支撑
                * 例如：[举出2-3个标签的数据论证]
              - 具体事例
                * 运用标签{tags_str}构建典型案例
                * 例如：[举出2-3个标签的案例展示]
              - 权威观点
                * 结合标签{tags_str}引用专业意见
                * 例如：[举出2-3个标签的观点引用]

           B. 分析角度：
              - 优点分析
                * 从标签{tags_str}中发掘亮点
                * 例如：[举出2-3个标签的优点分析]
              - 缺点剖析
                * 基于标签{tags_str}指出不足
                * 例如：[举出2-3个标签的缺点分析]
              - 特色发现
                * 通过标签{tags_str}凸显独特之处
                * 例如：[举出2-3个标签的特色提炼]

           C. 评价标准：
              - 专业标准
                * 将标签{tags_str}转化为评价指标
                * 例如：[举出2-3个标签的标准设定]
              - 社会影响
                * 分析标签{tags_str}的社会价值
                * 例如：[举出2-3个标签的影响分析]
              - 创新价值
                * 评估标签{tags_str}的创新程度
                * 例如：[举出2-3个标签的创新评价]

        # 三、写作方法
        1. 评论技巧运用
           - 如何做到客观公正？
           - 如何体现专业性？
           - 如何增强说服力？
           - 如何避免偏见？

        2. 语言表达技巧
           - 专业术语使用
           - 评价用语选择
           - 论证语言运用
           - 修辞手法应用

        # 四、标签运用策略
        1. 如何运用已有标签（{tags_str}）：
           - 每个标签可以评论哪些方面？
           - 标签之间如何组合评论？
           - 如何让标签自然融入评论？
           - 如何通过标签突出重点？
        """
        
def generate_creative_poetry_prompt(normal_tags, tag_infos):
    """生成创意诗歌写作提示"""
    # 获取所有附加信息作为诗歌主题
    poetry_subjects = []
    if tag_infos:
        for tag_info in tag_infos:
            poetry_subjects.append(f"{tag_info['tag']}：{tag_info['info']}")
    
    # 如果没有附加信息，使用普通标签或默认值
    if not poetry_subjects:
        if normal_tags and len(normal_tags) > 0:
            poetry_subjects = [f"关于{normal_tags[0]}的诗歌"]  # 使用第一个标签构造主题
        else:
            poetry_subjects = ["生活感悟"]  # 当没有任何标签时的默认值

    # 将所有主题组合成一个字符串
    poetry_subject = "、".join(poetry_subjects)

    tags_str = ', '.join([f'`{tag}`' for tag in normal_tags])
    
    return f"""请基于以下框架，生成一篇关于{poetry_subject}的创意诗歌写作指导：

        # 一、写作准备
        1. 头脑风暴与灵感收集
           A. 小组讨论建议：
              - 围绕标签{tags_str}展开讨论
              - 每人分享对标签的第一印象
              - 交流标签引发的个人记忆
              - 探讨标签间可能的情感联系
              - 记录讨论中产生的新观点

           B. 个人故事探索：
              - 这些标签让你想起什么经历？
              - 与标签相关的情感记忆有哪些？
              - 生活中的哪些细节与标签呼应？
              - 如何将个人故事诗意化？

           C. 标签解读（{tags_str}）：
              - 每个标签能唤起什么样的意象？
              - 标签之间有什么有趣的联系？
              - 这些标签如何转化为诗意表达？

           D. 情感深化：
              - 记录与标签相关的情感体验
              - 探索情感的多层次含义
              - 思考情感的普遍性与独特性
              - 寻找情感的具象表达方式

        2. 主题凝练
           A. 个人视角：
              - 你与这些标签的独特联系是什么？
              - 想要表达的核心情感是什么？
              - 个人经历如何赋予标签新的意义？

           B. 普遍意义：
              - 如何让个人经历产生共鸣？
              - 个人故事中的普遍主题是什么？
              - 如何平衡个性与共性？

        3. 诗歌形式选择
           A. 传统诗歌：
              - 古体诗（五言、七言）
              - 现代诗
              - 自由诗
              - 意象诗
              - 叙事诗

           B. 实验性形式：
              - 视觉诗
              - 声音诗
              - 混合体裁
              - 新媒体诗歌

        # 二、创作规划
        1. 诗歌结构设计
           A. 开篇设计：
              - 如何用标签创造强烈的开场？
                * 从标签{tags_str}中选择最具冲击力的意象
                * 例如：[举出2-3个标签组合的开场意象]
              - 如何设置诗歌基调？
                * 利用标签{tags_str}营造整体氛围
                * 例如：[举出2-3个标签设置情感基调的方式]
              - 如何引发读者兴趣？
                * 通过标签{tags_str}创造悬念或疑问
                * 例如：[举出2-3个标签引发兴趣的方式]

           B. 发展部分：
              - 意象的递进关系
                * 基于标签{tags_str}构建意象链
                * 例如：[举出2-3个标签的意象递进示例]
              - 情感的层次展开
                * 利用标签{tags_str}深化情感体验
                * 例如：[举出2-3个标签的情感层次展开]
              - 节奏的变化安排
                * 通过标签{tags_str}控制节奏快慢
                * 例如：[举出2-3个标签的节奏变化示例]
              - 标签的交织运用
                * 将不同标签{tags_str}巧妙组合
                * 例如：[举出2-3个标签的组合运用方式]

           C. 结尾构思：
              - 如何达到诗意升华？
                * 整合标签{tags_str}的深层含义
                * 例如：[举出2-3个标签的升华方式]
              - 如何给读者留下思考空间？
                * 用标签{tags_str}创造开放性意境
                * 例如：[举出2-3个标签的开放式结尾]
              - 如何实现首尾呼应？
                * 通过标签{tags_str}形成循环意象
                * 例如：[举出2-3个标签的呼应技巧]

        2. 诗歌元素运用
           A. 意象塑造：
              - 如何将标签转化为鲜活意象？
                * 挖掘标签{tags_str}的形象特征
                * 例如：[举出2-3个标签转化为意象的示例]
              - 如何创造独特的比喻？
                * 将标签{tags_str}与新鲜事物关联
                * 例如：[举出2-3个标签的比喻创新]
              - 如何运用象征手法？
                * 赋予标签{tags_str}象征意义
                * 例如：[举出2-3个标签的象征运用]

           B. 声音设计：
              - 韵律安排
                * 利用标签{tags_str}创造音韵美
                * 例如：[举出2-3个标签的韵律设计]
              - 音乐性处理
                * 通过标签{tags_str}营造声音效果
                * 例如：[举出2-3个标签的音乐性处理]
              - 朗读效果考虑
                * 基于标签{tags_str}设计朗读节奏
                * 例如：[举出2-3个标签的朗读效果]

           C. 节奏把控：
              - 行句长短变化
                * 根据标签{tags_str}设计句式长短
                * 例如：[举出2-3个标签的句式变化]
              - 停顿安排
                * 利用标签{tags_str}设置自然停顿
                * 例如：[举出2-3个标签的停顿设计]
              - 重复与变奏
                * 通过标签{tags_str}创造重复效果
                * 例如：[举出2-3个标签的重复变奏]

        3. 情感与意境营造
           A. 情感表达：
              - 直接抒情
                * 用标签{tags_str}表达真挚情感
                * 例如：[举出2-3个标签的直接抒情]
              - 含蓄表达
                * 通过标签{tags_str}暗示情感
                * 例如：[举出2-3个标签的含蓄表达]
              - 情感转折
                * 利用标签{tags_str}设计情感变化
                * 例如：[举出2-3个标签的情感转折]

           B. 意境创造：
              - 空间意境
                * 运用标签{tags_str}营造空间感
                * 例如：[举出2-3个标签的空间营造]
              - 时间意境
                * 通过标签{tags_str}表现时间流逝
                * 例如：[举出2-3个标签的时间表现]
              - 虚实结合
                * 将标签{tags_str}虚实交织
                * 例如：[举出2-3个标签的虚实结合]

        # 三、创作技巧
        1. 语言运用
           A. 词语选择：
              - 如何选择富有诗意的词语？
              - 如何避免陈词滥调？
              - 如何创造新鲜表达？

           B. 修辞手法：
              - 比喻的创新运用
              - 隐喻的深层设计
              - 象征的巧妙安排
              - 对偶的灵活使用

        2. 意境营造
           - 如何通过细节创造氛围？
           - 如何让抽象概念具象化？
           - 如何实现虚实结合？

        # 四、标签运用策略
        1. 标签转化建议
           - 如何将标签{tags_str}转化为诗歌元素？
           - 如何让标签之间产生诗意联系？
           - 如何避免标签生硬植入？

        2. 创新尝试
           - 标签的反向思考
           - 标签的跨界联想
           - 标签的多重解读
        """

def generate_creative_novel_prompt(normal_tags, tag_infos):
    """生成创意小说写作提示"""
    # 获取所有附加信息作为小说主题
    novel_subjects = []
    if tag_infos:
        for tag_info in tag_infos:
            novel_subjects.append(f"{tag_info['tag']}：{tag_info['info']}")
    
    # 如果没有附加信息，使用普通标签或默认值
    if not novel_subjects:
        if normal_tags and len(normal_tags) > 0:
            novel_subjects = [f"关于{normal_tags[0]}的故事"]  # 使用第一个标签构造主题
        else:
            novel_subjects = ["一个关于成长的故事"]  # 当没有任何标签时的默认值

    # 将所有主题组合成一个字符串
    novel_subject = "、".join(novel_subjects)

    tags_str = ', '.join([f'`{tag}`' for tag in normal_tags])
    
    return f"""请基于以下框架，生成一篇关于{novel_subject}的创意小说写作指导：

        # 一、创意激发
        1. 灵感来源探索
           A. 标签解读与联想（{tags_str}）：
              - 每个标签可能蕴含的故事元素
              - 标签之间有趣的组合可能
              - 标签引发的个人记忆和感受
              - 标签背后的深层含义

           B. 跨界灵感收集：
              - 相关电影、小说、戏剧作品
              - 新闻事件与社会现象
              - 艺术作品与音乐启发
              - 生活观察与个人经历

           C. 创意发散练习：
              - 标签组合的"what if"练习
              - 角色背景故事构想
              - 场景细节想象
              - 情节可能性探索

        2. 故事定位
           A. 类型选择：
              - 写实主义
              - 魔幻现实主义
              - 科幻小说
              - 悬疑推理
              - 青春成长
              - 历史演义
              - 奇幻冒险

           B. 风格确定：
              - 叙事语气
              - 写作风格
              - 情感基调
              - 节奏把控

        # 二、故事构建
        1. 核心要素设计
           A. 人物塑造：
              - 主要人物：
                * 用标签{tags_str}设计性格特征
                * 例如：[举出2-3个标签塑造性格的示例]
                * 通过标签{tags_str}构建背景故事
                * 例如：[举出2-3个标签设计背景的示例]
                * 利用标签{tags_str}规划成长轨迹
                * 例如：[举出2-3个标签展现成长的示例]

              - 配角设定：
                * 基于标签{tags_str}设计配角特点
                * 例如：[举出2-3个标签设计配角的示例]
                * 用标签{tags_str}构建人物关系
                * 例如：[举出2-3个标签设计关系的示例]
                * 通过标签{tags_str}突出配角作用
                * 例如：[举出2-3个标签凸显作用的示例]

              - 人物关系：
                * 利用标签{tags_str}设计矛盾冲突
                * 例如：[举出2-3个标签设计冲突的示例]
                * 通过标签{tags_str}展现关系发展
                * 例如：[举出2-3个标签展现发展的示例]
                * 用标签{tags_str}创造关系转折
                * 例如：[举出2-3个标签设计转折的示例]

           B. 情节架构：
              - 主要情节线：
                * 用标签{tags_str}设计核心冲突
                * 例如：[举出2-3个标签设计冲突的示例]
                * 通过标签{tags_str}规划发展脉络
                * 例如：[举出2-3个标签规划发展的示例]
                * 利用标签{tags_str}设计高潮场景
                * 例如：[举出2-3个标签设计高潮的示例]

              - 次要情节线：
                * 基于标签{tags_str}设计辅助故事
                * 例如：[举出2-3个标签设计辅线的示例]
                * 用标签{tags_str}铺设情感线索
                * 例如：[举出2-3个标签设计感情的示例]
                * 通过标签{tags_str}埋设伏笔
                * 例如：[举出2-3个标签设置伏笔的示例]

           C. 场景设置：
              - 时空背景：
                * 利用标签{tags_str}构建历史背景
                * 例如：[举出2-3个标签设计背景的示例]
                * 用标签{tags_str}营造地理环境
                * 例如：[举出2-3个标签描绘环境的示例]
                * 通过标签{tags_str}渲染社会氛围
                * 例如：[举出2-3个标签营造氛围的示例]

              - 场景描写：
                * 基于标签{tags_str}刻画环境细节
                * 例如：[举出2-3个标签描写细节的示例]
                * 用标签{tags_str}营造场景氛围
                * 例如：[举出2-3个标签营造氛围的示例]
                * 通过标签{tags_str}设计象征意义
                * 例如：[举出2-3个标签设计象征的示例]

        2. 结构规划
           A. 开篇设计：
              - 如何抓住读者注意力？
                * 从标签{tags_str}中选择最具冲击力的元素
                * 例如：[举出2-3个标签设计开场的示例]
              - 如何介绍人物与背景？
                * 通过标签{tags_str}自然引入人物和背景
                * 例如：[举出2-3个标签引入设定的示例]
              - 如何埋下故事伏笔？
                * 利用标签{tags_str}设置前期悬念
                * 例如：[举出2-3个标签设置悬念的示例]

           B. 情节发展：
              - 第一阶段：铺垫与悬念
                * 用标签{tags_str}设计铺垫情节
                * 例如：[举出2-3个标签设计铺垫的示例]
              - 第二阶段：冲突加剧
                * 通过标签{tags_str}推动矛盾升级
                * 例如：[举出2-3个标签推动冲突的示例]
              - 第三阶段：高潮迭起
                * 利用标签{tags_str}设计高潮场景
                * 例如：[举出2-3个标签设计高潮的示例]

           C. 结局构思：
              - 如何解决主要矛盾？
                * 通过标签{tags_str}设计矛盾解决方式
                * 例如：[举出2-3个标签解决矛盾的示例]
              - 如何安排人物命运？
                * 基于标签{tags_str}设计人物结局
                * 例如：[举出2-3个标签设计结局的示例]
              - 如何实现主题升华？
                * 利用标签{tags_str}深化故事主题
                * 例如：[举出2-3个标签升华主题的示例]

        # 三、写作技巧
        1. 叙述视角选择
           - 第一人称：沉浸感与局限性
           - 第三人称限制性视角：聚焦与神秘感
           - 第三人称全知视角：全景与控制
           - 多视角叙述：丰富性与复杂度

        2. 语言风格
           - 描写技巧：细节描写、环境描写、心理描写
           - 对话设计：个性化表达、情感传递、关系展现
           - 节奏控制：长短句搭配、段落节奏、情感起伏
           - 修辞运用：比喻、象征、夸张等修辞手法

        # 四、标签运用策略
        1. 标签融入建议
           - 如何将标签{tags_str}自然融入故事
           - 标签之间的关联设计
           - 避免标签生硬植入的方法
           - 标签与主题的呼应

        2. 创新运用
           - 标签的反向思考与突破
           - 标签间的创意组合
           - 标签的象征意义开发
           - 标签与情节的有机结合
        """
        
def generate_creative_script_prompt(normal_tags, tag_infos):
    """生成创意剧本写作提示"""
    # 获取所有附加信息作为剧本主题
    script_subjects = []
    if tag_infos:
        for tag_info in tag_infos:
            script_subjects.append(f"{tag_info['tag']}：{tag_info['info']}")
    
    # 如果没有附加信息，使用普通标签或默认值
    if not script_subjects:
        if normal_tags and len(normal_tags) > 0:
            script_subjects = [f"关于{normal_tags[0]}的故事"]  # 使用第一个标签构造主题
        else:
            script_subjects = ["一个关于成长的故事"]  # 当没有任何标签时的默认值

    # 将所有主题组合成一个字符串
    script_subject = "、".join(script_subjects)

    tags_str = ', '.join([f'`{tag}`' for tag in normal_tags])
    
    return f"""请基于以下框架，生成一篇关于{script_subject}的创意剧本写作指导：

        # 一、前期准备
        1. 剧本定位
           A. 基本要素确定：
              - 类型：话剧、影视剧、广播剧等
              - 时长：短剧、中篇、长篇
              - 受众：目标观众群体
              - 主题：核心思想与情感

           B. 风格选择：
              - 写实主义
              - 荒诞戏剧
              - 象征主义
              - 实验性戏剧
              - 音乐剧等

        2. 创意发想
           A. 标签解读（{tags_str}）：
              - 每个标签可能的戏剧性元素
              - 标签之间的戏剧性碰撞
              - 标签的象征意义开发
              - 标签与主题的呼应

           B. 灵感来源：
              - 生活观察与经历
              - 新闻事件与社会现象
              - 文学作品与艺术启发
              - 历史故事与民间传说

        # 二、剧本元素设计
        1. 人物塑造
           A. 主要人物：
              - 性格特征与背景故事
                * 用标签{tags_str}设计人物性格
                * 例如：[举出2-3个标签塑造性格的示例]
              - 内心需求与行为动机
                * 通过标签{tags_str}构建动机链
                * 例如：[举出2-3个标签设计动机的示例]
              - 人物成长与转变
                * 利用标签{tags_str}规划成长轨迹
                * 例如：[举出2-3个标签展现转变的示例]

           B. 配角设计：
              - 与主角的关系
                * 基于标签{tags_str}设计人物关系
                * 例如：[举出2-3个标签设计关系的示例]
              - 戏剧功能定位
                * 通过标签{tags_str}明确配角作用
                * 例如：[举出2-3个标签定位功能的示例]
              - 个性特征
                * 运用标签{tags_str}塑造配角特点
                * 例如：[举出2-3个标签设计特征的示例]

           C. 人物关系：
              - 主要矛盾关系
                * 利用标签{tags_str}设计核心冲突
                * 例如：[举出2-3个标签设计冲突的示例]
              - 次要关系网络
                * 通过标签{tags_str}构建关系网
                * 例如：[举出2-3个标签设计网络的示例]
              - 关系发展变化
                * 用标签{tags_str}推动关系演变
                * 例如：[举出2-3个标签展现变化的示例]

        2. 情节构建
           A. 主要情节线：
              - 核心冲突设置
                * 从标签{tags_str}中提炼核心矛盾
                * 例如：[举出2-3个标签设计矛盾的示例]
              - 戏剧性事件安排
                * 利用标签{tags_str}设计关键事件
                * 例如：[举出2-3个标签设计事件的示例]
              - 转折点设计
                * 通过标签{tags_str}创造转折点
                * 例如：[举出2-3个标签设计转折的示例]

           B. 次要情节线：
              - 辅助性故事
                * 用标签{tags_str}设计副线剧情
                * 例如：[举出2-3个标签设计副线的示例]
              - 感情线设计
                * 基于标签{tags_str}构建情感线
                * 例如：[举出2-3个标签设计感情的示例]
              - 悬念铺垫
                * 通过标签{tags_str}设置悬念
                * 例如：[举出2-3个标签设计悬念的示例]

        3. 场景设计
           A. 空间场景：
              - 主要场景设定
                * 利用标签{tags_str}营造场景氛围
                * 例如：[举出2-3个标签设计场景的示例]
              - 场景转换安排
                * 通过标签{tags_str}实现场景转换
                * 例如：[举出2-3个标签转换场景的示例]
              - 道具与布景
                * 用标签{tags_str}设计关键道具
                * 例如：[举出2-3个标签设计道具的示例]

           B. 时间设计：
              - 时间跨度
                * 基于标签{tags_str}规划时间线
                * 例如：[举出2-3个标签设计时间的示例]
              - 时序安排
                * 利用标签{tags_str}处理时间顺序
                * 例如：[举出2-3个标签安排时序的示例]
              - 节奏控制
                * 通过标签{tags_str}把控剧情节奏
                * 例如：[举出2-3个标签控制节奏的示例]

        # 三、剧本结构
        1. 整体架构
           A. 开场设计：
              - 观众注意力的抓取
                * 从标签{tags_str}中选择冲击性元素
                * 例如：[举出2-3个标签设计开场的示例]
              - 基本信息的交代
                * 通过标签{tags_str}引入背景信息
                * 例如：[举出2-3个标签交代信息的示例]
              - 冲突的引入
                * 利用标签{tags_str}埋下冲突种子
                * 例如：[举出2-3个标签引入冲突的示例]

           B. 发展过程：
              - 第一阶段：铺垫与悬念
                * 用标签{tags_str}设计铺垫情节
                * 例如：[举出2-3个标签铺垫情节的示例]
              - 第二阶段：冲突加剧
                * 通过标签{tags_str}推动矛盾升级
                * 例如：[举出2-3个标签升级冲突的示例]
              - 第三阶段：高潮迭起
                * 整合标签{tags_str}创造高潮
                * 例如：[举出2-3个标签设计高潮的示例]

           C. 结局处理：
              - 主要矛盾的解决
                * 利用标签{tags_str}化解核心冲突
                * 例如：[举出2-3个标签解决矛盾的示例]
              - 人物命运的安排
                * 基于标签{tags_str}设计人物结局
                * 例如：[举出2-3个标签安排结局的示例]
              - 主题的升华
                * 通过标签{tags_str}深化主题内涵
                * 例如：[举出2-3个标签升华主题的示例]

        2. 场景编排
           - 场景顺序安排
              * 用标签{tags_str}设计场景顺序
              * 例如：[举出2-3个标签安排顺序的示例]
           - 场景之间的过渡
              * 通过标签{tags_str}实现自然过渡
              * 例如：[举出2-3个标签设计过渡的示例]
           - 戏剧节奏的控制
              * 利用标签{tags_str}调节整体节奏
              * 例如：[举出2-3个标签控制节奏的示例]

        # 四、对话创作
        1. 对话设计原则
           - 推动情节发展
              * 用标签{tags_str}设计关键对话
              * 例如：[举出2-3个标签设计对话的示例]
           - 展现人物性格
              * 通过标签{tags_str}体现性格特征
              * 例如：[举出2-3个标签展现性格的示例]
           - 制造戏剧冲突
              * 利用标签{tags_str}创造对话冲突
              * 例如：[举出2-3个标签设计冲突的示例]

        # 四、对话创作
        1. 对话设计原则
           - 推动情节发展
           - 展现人物性格
           - 制造戏剧冲突
           - 融入标签元素

        2. 对话技巧
           - 个性化语言
           - 潜台词运用
           - 节奏与韵律
           - 标签语言的转化

        # 五、舞台呈现
        1. 视觉设计
           - 舞台布景
           - 道具设计
           - 灯光效果
           - 标签的视觉化

        2. 声音设计
           - 音效规划
           - 背景音乐
           - 声音效果
           - 标签的听觉化

        # 六、标签运用策略
        1. 标签融入方法
           - 标签{tags_str}的戏剧化转换
           - 标签间的互动设计
           - 标签与主题的呼应
           - 避免生硬植入

        2. 创新运用
           - 标签的多维度开发
           - 标签的象征性表达
           - 标签的戏剧性转化
           - 标签与剧情的有机结合
        """

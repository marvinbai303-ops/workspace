from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os


OUT = Path('/Users/yangguang/Documents/Codex/workspace/基金经理研究/ima_three_memos_long_images')
OUT.mkdir(parents=True, exist_ok=True)
FONT_CJK = '/System/Library/Fonts/Hiragino Sans GB.ttc'
FONT_LATIN = '/System/Library/Fonts/HelveticaNeue.ttc'


def font(size, bold=False):
    path = FONT_CJK if os.path.exists(FONT_CJK) else FONT_LATIN
    return ImageFont.truetype(path, size=size, index=1 if bold and path == FONT_CJK else 0)


F = {
    'title': font(48, True), 'subtitle': font(25), 'section': font(29, True),
    'body': font(25), 'body_bold': font(25, True), 'small': font(20),
    'small_bold': font(20, True), 'tiny': font(17),
}
BG, INK, MUTED, LINE, WHITE = '#F5F7FA', '#17212B', '#65717D', '#D7DEE5', '#FFFFFF'


def rr(draw, box, radius=18, fill=WHITE, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text(draw, xy, s, f, fill=INK, anchor=None):
    draw.text(xy, s, font=f, fill=fill, anchor=anchor)


def wrap_lines(draw, s, f, max_width):
    lines, cur = [], ''
    for ch in s:
        if ch == '\n':
            lines.append(cur)
            cur = ''
        elif not cur or draw.textlength(cur + ch, font=f) <= max_width:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def paragraph(draw, x, y, s, f, fill, max_width, line_gap=9):
    for line in wrap_lines(draw, s, f, max_width):
        text(draw, (x, y), line, f, fill)
        y += f.size + line_gap
    return y


def header(draw, title, accent, subtitle):
    text(draw, (72, 65), '基金经理研究｜交流纪要', F['small_bold'], accent)
    text(draw, (72, 108), title, F['title'])
    text(draw, (72, 184), subtitle, F['subtitle'], MUTED)
    draw.line((72, 238, 1008, 238), fill=accent, width=5)


def core_box(draw, y, accent, body):
    rr(draw, (72, y, 1008, y + 165), 22, fill=accent)
    text(draw, (104, y + 25), '核心框架', F['small_bold'], WHITE)
    paragraph(draw, 104, y + 68, body, F['body_bold'], WHITE, 850, 10)
    return y + 195


def section(draw, y, label, accent):
    draw.rounded_rectangle((72, y + 5, 80, y + 34), radius=4, fill=accent)
    text(draw, (96, y), label, F['section'])
    return y + 54


def flow(draw, y, steps, accent):
    x0, w, gap = 72, 270, 45
    for i, (head, body) in enumerate(steps):
        x = x0 + i * (w + gap)
        rr(draw, (x, y, x + w, y + 145), 18, fill=WHITE, outline=LINE, width=2)
        draw.ellipse((x + 22, y + 22, x + 58, y + 58), fill=accent)
        text(draw, (x + 40, y + 40), str(i + 1), F['small_bold'], WHITE, anchor='mm')
        text(draw, (x + 76, y + 22), head, F['small_bold'])
        paragraph(draw, x + 22, y + 72, body, F['small'], MUTED, w - 44, 7)
        if i < len(steps) - 1:
            text(draw, (x + w + 14, y + 60), '→', F['section'], accent)
    return y + 175


def cards(draw, y, items, accent, card_h=170):
    gap, cols = 18, 2
    w = (936 - gap) // 2
    for i, (head, body) in enumerate(items):
        row, col = divmod(i, cols)
        x, yy = 72 + col * (w + gap), y + row * (card_h + gap)
        rr(draw, (x, yy, x + w, yy + card_h), 18, fill=WHITE, outline=LINE, width=2)
        draw.rounded_rectangle((x, yy, x + w, yy + 9), radius=5, fill=accent)
        text(draw, (x + 22, yy + 26), head, F['small_bold'])
        paragraph(draw, x + 22, yy + 70, body, F['small'], MUTED, w - 44, 8)
    rows = (len(items) + 1) // 2
    return y + rows * (card_h + gap) - gap + 20


def bullets(draw, y, items, accent, gap=14):
    for item in items:
        text(draw, (80, y + 4), '•', F['body_bold'], accent)
        lines = wrap_lines(draw, item, F['body'], 864)
        for i, line in enumerate(lines):
            text(draw, (116, y + i * 38), line, F['body'])
        y += max(46, len(lines) * 38) + gap
    return y


def finish(draw, H, accent):
    y = H - 92
    draw.line((72, y, 1008, y), fill=LINE, width=2)
    text(draw, (72, y + 26), '基金经理研究｜核心投资框架与观点', F['tiny'], MUTED)
    text(draw, (1008, y + 26), '交流纪要', F['tiny'], accent, anchor='ra')


def make_minsheng():
    W, H, accent = 1080, 2150, '#9A3B32'
    img, d = Image.new('RGB', (W, H), BG), None
    d = ImageDraw.Draw(img)
    header(d, '民生加银刘浩交流', accent, '全球视角与深度价值：关注现金流、资产负债表与长期回报')
    y = core_box(d, 280, accent, '组合由全球定价资源、深度价值和消费/平台型公司构成；选股重视资产质量、现金流、安全边际与股东回报。')

    y = section(d, y, '组合结构', accent)
    y = flow(d, y, [
        ('全球定价资源', '关注全球供需、资本开支与长期回报。'),
        ('深度价值', '以资产负债表、现金流和估值保护为基础。'),
        ('消费与平台', '关注品牌、平台属性与跨周期经营能力。'),
    ], accent)

    y = section(d, y, '选股标准', accent)
    y = cards(d, y, [
        ('资产与现金流', '关注资产价值、现金储备、自由现金流和持续分红/回购。'),
        ('估值与安全边际', '低流动性和低关注度不是障碍，关键是价格是否提供足够保护。'),
        ('股东回报', '管理层能否持续把现金回报股东，是判断公司质量的重要标准。'),
        ('全球可比性', '优先研究有全球对标对象、能够用长期尺度判断的行业。'),
    ], accent, 170)

    y = section(d, y, '行业观点', accent)
    cards(d, y, [
        ('银行', '跨境网络和全球客户连接更重要；国内银行不能只看低PB和高股息，还要评估资产质量。'),
        ('资源', '不只看短期供需和价格，重点评估资本开支、回收周期与长期可持续回报。'),
        ('消费', '对只依赖国内需求的消费品更谨慎，关注品牌能否跨市场、跨周期验证。'),
        ('制造与汽车', '思源电气、重卡、摩托车/两轮车等案例，关注治理、海外竞争力与产业位置。'),
    ], accent, 175)
    finish(d, H, accent)
    img.save(OUT / '民生加银刘浩交流.png', quality=96)


def make_wanjia():
    W, H, accent = 1080, 2150, '#276A6A'
    img, d = Image.new('RGB', (W, H), BG), None
    d = ImageDraw.Draw(img)
    header(d, '万家基金乔良路演', accent, '从基金中位数到可实现组合：估算持仓、精选基金、等权合成与约束优化')
    y = core_box(d, 280, accent, '方法包括：估算场外基金当期持仓，从约5—6千只权益基金中筛选约300只，等权合成股票组合，并加入行业、风格、个股、换手及交易成本约束。')

    y = section(d, y, '基金选择', accent)
    y = flow(d, y, [
        ('基金中位数', '每日排序并取中间基金，代表主动权益的中位水平。'),
        ('平均持仓', '全市场持仓平均会平滑阶段性风格变化。'),
        ('精选基金', '从全市场基金中筛选更有信息含量的样本。'),
    ], accent)

    y = section(d, y, '组合构建', accent)
    y = flow(d, y, [
        ('估算持仓', '场外基金披露滞后，先估算当期持仓。'),
        ('等权合成', '将入选基金的股票持仓按等权合成。'),
        ('组合优化', '行业、风格、个股、换手和交易成本共同进入优化。'),
    ], accent)

    y = section(d, y, '策略组合方式', accent)
    cards(d, y, [
        ('偏股中位数策略', '承担趋势与成长暴露，获取主动权益中位数的长期收益。'),
        ('红利与质量策略', '将红利、自由现金流和PB—ROE等指标结合使用。'),
        ('可转债量化策略', '作为权益量化的补充，降低与小盘股票策略的同步性。'),
        ('结构保持稳定', '不依赖大幅风格轮动，关注长期收益与回撤之间的平衡。'),
    ], accent, 170)
    finish(d, H, accent)
    img.save(OUT / '万家基金乔良路演.png', quality=96)


def make嘉实():
    W, H, accent = 1080, 2200, '#4C4A87'
    img, d = Image.new('RGB', (W, H), BG), None
    d = ImageDraw.Draw(img)
    header(d, '嘉实基金龙昌伦交流', accent, '指数与量化：按指数结构和风格定制模型，交易系统决定超额兑现')
    y = core_box(d, 280, accent, '指数结构、风格暴露、因子模型、组合约束和交易系统共同决定可实现超额；不同指数不能机械复用同一套方法。')

    y = section(d, y, '方法框架', accent)
    y = flow(d, y, [
        ('指数结构', '先区分市值、行业覆盖、容量和可交易性。'),
        ('风格模型', '成长、价值、质量、小盘是主要分析维度。'),
        ('组合与交易', '通过约束、换手管理和交易系统实现信号。'),
    ], accent)
    y = bullets(d, y, [
        '300的方法逐步接近800的做法，方法不再局限于传统多因子模板。',
        '相较于粗粒度行业轮动，风格暴露更适合被模型识别、解释和控制。',
    ], accent)

    y = section(d, y, '指数差异', accent)
    y = cards(d, y, [
        ('沪深300', '大市值、成分更集中，主动偏离空间相对小。'),
        ('中证500', '竞争充分，超额实现对方法和交易效率要求较高。'),
        ('中证800', '规模和方法承载较好，适合将风格模型做成稳定增强。'),
        ('中证1000', '中小盘属性更强，对换手、系统和交易通道更敏感。'),
    ], accent, 160)

    y = section(d, y, '风格与交易观点', accent)
    cards(d, y, [
        ('四个风格维度', '成长、价值、质量、小盘构成可解释的风格工具箱。'),
        ('指数设计影响暴露', 'A500覆盖更广的三级行业，整体市值比300偏小，风格更积极。'),
        ('模型与约束配合', '模型识别风格变化，组合约束控制偏离程度。'),
        ('交易决定兑现', '系统容量、换手承载、券商通道和交易摩擦会影响实际超额。'),
    ], accent, 170)
    finish(d, H, accent)
    img.save(OUT / '嘉实基金龙昌伦交流.png', quality=96)


if __name__ == '__main__':
    make_minsheng()
    make_wanjia()
    make嘉实()
    print(OUT)

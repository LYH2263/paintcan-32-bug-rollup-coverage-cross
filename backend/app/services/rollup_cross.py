"""Multi-room rollup helpers."""


def sum_room_totals(rows):
    """合计净面积与升数 = 各房分列之和。

    各房在 estimate_room 阶段已用自己的涂布率/遍数算好 liters 与 net_m2，
    合计只能逐房相加，不得拿某一房的涂布率/遍数去套汇总净面积。
    """
    if not rows:
        return 0.0, 0.0
    total_net = round(sum(float(x["net_m2"]) for x in rows), 2)
    total_liters = round(sum(float(x["liters"]) for x in rows), 2)
    return total_liters, total_net

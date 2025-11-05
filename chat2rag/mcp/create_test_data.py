import asyncio
import random

from tortoise import Tortoise

from .config import SETTINGS
from .models.device import Device
from .models.entity import Entity
from .models.scene import Scene

# 场景列表
scenes = [
    "机场",
    "医院",
    "学校",
    "商场",
    "公园",
    "车站",
    "酒店",
    "餐厅",
    "图书馆",
    "博物馆",
]

entities_data = [
    ["卫生间A", "厕所", "WC、卫生间、洗手间", True],
    ["卫生间B", "厕所", "WC、公共卫生间、洗手间", True],
    ["餐厅区域", "餐厅", "用餐区、饭厅、食堂", True],
    ["休息区", "休息处", "休闲区、歇脚处、等候区", True],
    ["售票处", "票务中心", "购票处、售票窗口", False],
    ["服务台", "问询处", "服务中心、咨询台、帮助台", False],
    ["电梯A", "电梯", "升降机、直梯", True],
    ["扶梯B", "扶梯", "自动扶梯、电动楼梯", True],
    ["北门入口", "入口", "北门、进口、门口", False],
    ["停车场A区", "停车场", "车库、泊车区", True],
]


async def create_test_data():
    global scenes, entities_data
    # 连接数据库
    await Tortoise.init(config=SETTINGS.TORTOISE_ORM)

    # 创建场景数据
    for scene_name in scenes:
        scene, created = await Scene.get_or_create(name=scene_name)

        # 为每个场景创建10-30个设备
        if created:
            num_devices = random.randint(10, 30)
            for i in range(num_devices):
                device_vin = f"HTYW{random.randint(100000, 999999)}A{random.randint(100000, 999999)}"
                await Device.create(vin=device_vin, scene=scene)
                print(f"  - 创建设备: {device_vin}")

    # 打印统计信息
    scene_count = await Scene.all().count()
    device_count = await Device.all().count()
    print(f"\n总计: {scene_count} 个场景, {device_count} 个设备")

    # 创建实体数据，获取所有场景
    scenes = await Scene.all()
    if not scenes:
        print("警告: 没有找到任何场景。请先运行场景测试数据创建脚本。")

    # 创建实体数据
    for name, common_name, alias, allow_nearest in entities_data:
        entity, created = await Entity.get_or_create(
            name=name,
            defaults={
                "common_name": common_name,
                "alias": alias,
                "allow_nearest": allow_nearest,
            },
        )

        status = "创建" if created else "已存在"
        print(
            f"{status} 实体: {name} (通用名: {common_name}, 别名: {alias}, 允许最近匹配: {allow_nearest})"
        )

        # 将实体随机关联到1-3个场景
        if created and scenes:
            # 随机选择1-3个场景
            selected_scenes = random.sample(
                scenes, min(random.randint(1, 3), len(scenes))
            )
            # 添加场景关联
            await entity.scenes.add(*selected_scenes)

            scene_names = [scene.name for scene in selected_scenes]
            print(f"  - 关联到场景: {', '.join(scene_names)}")

    # 打印统计信息
    entity_count = await Entity.all().count()

    print(f"\n总计: {entity_count} 个实体")
    # 关闭连接
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(create_test_data())

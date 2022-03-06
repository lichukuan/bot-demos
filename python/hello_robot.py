#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import os.path
from typing import Dict, List

import aiohttp
import qqbot
from qqbot.core.util.yaml_util import YamlUtil
from qqbot.model.message import MessageEmbed, MessageEmbedField, MessageEmbedThumbnail, CreateDirectMessageRequest, \
    MessageArk, MessageArkKv, MessageArkObj, MessageArkObjKv

test_config = YamlUtil.read(os.path.join(os.path.dirname(__file__), "config.yaml"))


async def _message_handler(event, message: qqbot.Message):
    """
    定义事件回调的处理

    :param event: 事件类型
    :param message: 事件对象（如监听消息是Message对象）
    """
    msg_api = qqbot.AsyncMessageAPI(t_token, False)
    # 打印返回信息
    qqbot.logger.info("event %s" % event + ",receive message %s" % message.content)

    # 根据指令触发不同的推送消息
    if "/推送深圳天气" in message.content:
        weather = await get_weather("深圳")
        await send_weather_ark_message(weather, message.channel_id, message.id)

    if "/推送上海天气" in message.content:
        weather = await get_weather("上海")
        await send_weather_ark_message(weather, message.channel_id, message.id)

    if "/推送北京天气" in message.content:
        weather = await get_weather("北京")
        await send_weather_ark_message(weather, message.channel_id, message.id)

    if "/私信推送天气" in message.content:
        weather = await get_weather("北京")
        await send_weather_embed_direct_message(weather, message.guild_id, message.author.id)


async def _create_ark_obj_list(weather_dict) -> List[MessageArkObj]:
    obj_list = []

    obj = MessageArkObj()
    obj_kv_list = []
    obj_kv = MessageArkObjKv()
    obj_kv.key = "desc"
    obj_kv.value = weather_dict['result']['citynm'] + " " + weather_dict['result']['weather']
    obj_kv_list.append(obj_kv)
    obj.obj_kv = obj_kv_list
    obj_list.append(obj)

    obj = MessageArkObj()
    obj_kv_list = []
    obj_kv = MessageArkObjKv()
    obj_kv.key = "desc"
    obj_kv.value = "当日温度区间：" + weather_dict['result']['temperature']
    obj_kv_list.append(obj_kv)
    obj.obj_kv = obj_kv_list
    obj_list.append(obj)

    obj = MessageArkObj()
    obj_kv_list = []
    obj_kv = MessageArkObjKv()
    obj_kv.key = "desc"
    obj_kv.value = "当前温度：" + weather_dict['result']['temperature_curr']
    obj_kv_list.append(obj_kv)
    obj.obj_kv = obj_kv_list
    obj_list.append(obj)

    obj = MessageArkObj()
    obj_kv_list = []
    obj_kv = MessageArkObjKv()
    obj_kv.key = "desc"
    obj_kv.value = "当前湿度：" + weather_dict['result']['humidity']
    obj_kv_list.append(obj_kv)
    obj.obj_kv = obj_kv_list
    obj_list.append(obj)

    return obj_list


async def _create_ark_kv_list(weather_dict) -> List[MessageArkKv]:
    kv_list = []
    kv = MessageArkKv()
    kv.key = "#DESC#"
    kv.value = "描述"
    kv_list.append(kv)

    kv = MessageArkKv()
    kv.key = "#PROMPT#"
    kv.value = "提示消息"
    kv_list.append(kv)

    kv = MessageArkKv()
    kv.key = "#LIST#"
    kv.obj = await _create_ark_obj_list(weather_dict)
    kv_list.append(kv)
    return kv_list


async def send_weather_ark_message(weather_dict, channel_id, message_id):
    """
    被动回复-子频道推送模版消息

    :param channel_id: 回复消息的子频道ID
    :param message_id: 回复消息ID
    :param weather_dict:天气消息
    """
    # 构造消息发送请求数据对象
    ark = MessageArk()
    # 模版ID=23
    ark.template_id = 23
    ark.kv = await _create_ark_kv_list(weather_dict)
    # 通过api发送回复消息
    send = qqbot.MessageSendRequest(content="", ark=ark, msg_id=message_id)
    msg_api = qqbot.AsyncMessageAPI(t_token, False)
    await msg_api.post_message(channel_id, send)


async def _create_embed_fields(weather_dict) -> List[MessageEmbedField]:
    fields = []
    field = MessageEmbedField()
    field.name = "当日温度区间：" + weather_dict['result']['temperature']
    fields.append(field)

    field = MessageEmbedField()
    field.name = "当前温度：" + weather_dict['result']['temperature_curr']
    fields.append(field)

    field = MessageEmbedField()
    field.name = "最高温度：" + weather_dict['result']['temp_high']
    fields.append(field)

    field = MessageEmbedField()
    field.name = "最低温度：" + weather_dict['result']['temp_low']
    fields.append(field)

    field = MessageEmbedField()
    field.name = "当前湿度：" + weather_dict['result']['humidity']
    fields.append(field)
    return fields


async def send_weather_embed_direct_message(weather_dict, guild_id, user_id):
    """
    被动回复-私信推送天气内嵌消息

    :param user_id: 用户ID
    :param weather_dict: 天气数据字典
    :param guild_id: 发送私信需要的源频道ID
    """
    # 构造消息发送请求数据对象
    embed = MessageEmbed()
    embed.title = weather_dict['result']['citynm'] + " " + weather_dict['result']['weather']
    embed.prompt = "天气消息推送"
    # 构造内嵌消息缩略图
    thumbnail = MessageEmbedThumbnail()
    thumbnail.url = weather_dict['result']['weather_icon']
    embed.thumbnail = thumbnail
    # 构造内嵌消息fields
    embed.fields = await _create_embed_fields(weather_dict)

    # 通过api发送回复消息
    send = qqbot.MessageSendRequest(embed=embed, content="")
    dms_api = qqbot.AsyncDmsAPI(t_token, False)
    direct_message_guild = await dms_api.create_direct_message(CreateDirectMessageRequest(guild_id, user_id))
    await dms_api.post_direct_message(direct_message_guild.guild_id, send)
    qqbot.logger.info("/私信推送天气内嵌消息 成功")


async def get_weather(city_name: str) -> Dict:
    """
    获取天气信息

    :return: 返回天气数据的json对象
    返回示例
    {
    "success":"1",
    "result":{
        "weaid":"1",
        "days":"2022-03-04",
        "week":"星期五",
        "cityno":"beijing",
        "citynm":"北京",
        "cityid":"101010100",
        "temperature":"13℃/-1℃",
        "temperature_curr":"10℃",
        "humidity":"17%",
        "aqi":"98",
        "weather":"扬沙转晴",
        "weather_curr":"扬沙",
        "weather_icon":"http://api.k780.com/upload/weather/d/30.gif",
        "weather_icon1":"",
        "wind":"西北风",
        "winp":"4级",
        "temp_high":"13",
        "temp_low":"-1",
        "temp_curr":"10",
        "humi_high":"0",
        "humi_low":"0",
        "weatid":"31",
        "weatid1":"",
        "windid":"7",
        "winpid":"4",
        "weather_iconid":"30"
        }
    }
    """
    weather_api_url = "http://api.k780.com/?app=weather.today&cityNm=" + city_name + "&appkey=10003&sign=b59bc3ef6191eb9f747dd4e83c99f2a4&format=json"
    async with aiohttp.ClientSession() as session:
        async with session.get(
                url=weather_api_url,
                timeout=5,
        ) as resp:
            content = await resp.text()
            content_json_obj = json.loads(content)
            return content_json_obj


# async的异步接口的使用示例
if __name__ == "__main__":
    t_token = qqbot.Token(test_config["token"]["appid"], test_config["token"]["token"])
    # @机器人后推送被动消息
    qqbot_handler = qqbot.Handler(
        qqbot.HandlerType.AT_MESSAGE_EVENT_HANDLER, _message_handler
    )
    qqbot.async_listen_events(t_token, False, qqbot_handler)

    # 定时推送主动消息
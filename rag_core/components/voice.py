# from haystack import component
# # from funasr import AutoModel


# @component
# class VoiceASR:
#     """语音识别"""

#     @component.output_types(response=str)
#     def run(self, audio_file: str):
#         """
#         语音识别
#         """
#         model = AutoModel(model="paraformer-zh", disable_update=True)
#         result = model.asr(audio_file)
#         return {"response": result}

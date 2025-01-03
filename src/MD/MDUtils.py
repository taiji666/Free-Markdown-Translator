from .Nodes import *
from .config import config
from .Utils import Patterns, get_arguments, expand_part, RawData, Pbar, shortedPath, get_size
import asyncio
from pathlib import Path
from .Translator import Translator
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
import copy
#文本解析
class MDAnalysis:
    def __init__(self, src_file: Path):
        self.src_file = src_file
        self.raw_data = None


    @staticmethod
    async def __generate_nodes(src_lines: list[str]) -> list[Node]:
        """
        扫描每行，依次为每行生成节点
        """
        is_front_matter = False
        # 在```包裹的代码块中
        is_code_block = False
        # 忽略翻译的部分，实际上和代码块内容差不多，只是连标识符都忽略了
        is_not_trans = False
        is_line_math = False
        is_insert_warnings = config.insert_warnings
        nodes = []
        for line in src_lines:
            if line.strip() == "---":
                is_front_matter = not is_front_matter
                nodes.append(TransparentNode(line))
                # 添加头部的机器翻译警告的占位符
                if not is_front_matter and is_insert_warnings:
                    nodes.append(TransparentNode("___HOLD_To_FILL_WARNING___"))
                    is_insert_warnings = False
                continue

            if line.startswith("```"):
                is_code_block = not is_code_block
                nodes.append(TransparentNode(line))
                continue

            if line.startswith("__do_not_translate__"):
                is_not_trans = not is_not_trans
                continue
            #处理行间公式
            if line.startswith("$$"):
                is_line_math = not is_line_math
                nodes.append(TransparentNode(line))
                continue

            # 处理front matter
            if is_front_matter:
                if line.startswith(tuple(config.front_matter_key_value_keys)):
                    nodes.append(KeyValueNode(line))
                elif line.startswith(tuple(config.front_matter_transparent_keys)):
                    nodes.append(TransparentNode(line))
                elif line.startswith(tuple(config.front_matter_key_value_array_keys)):
                    nodes.append(KeyValueArrayNode(line))
                else:
                    nodes.append(SolidNode(line))

            # 处理代码块
            elif is_code_block or is_not_trans or is_line_math:
                nodes.append(TransparentNode(line))

            else:
                # 空行或者图片、音频等不需要翻译的内容
                if len(line.strip()) == 0 or line.startswith(("<audio", "<img ")):
                    nodes.append(TransparentNode(line))
                # 图片或链接
                elif Patterns.ImageOrLink.search(line):
                    nodes.append(ImageOrLinkNode(line))
                elif line.strip().startswith("#"):  # 标题
                    nodes.append(TitleNode(line))
                    # 一级标题
                    if line.strip().startswith("# ") and is_insert_warnings:
                        nodes.append(TransparentNode("___HOLD_To_FILL_WARNING___"))
                        is_insert_warnings = False
                else:  # 普通文字
                    nodes.append(SolidNode(line))
        return nodes




    @staticmethod
    async def __handle_chunk(chunk: str) -> tuple[dict[int, str], dict[int, str], int]:
        """
        按文本块进行处理，将文本块分为跳过的部分和需要翻译的部分
        :param chunk: 文本块
        :return:
        """
        parts: list[str] = Patterns.Skipped.split(chunk)
        # 跳过的部分
        skipped_parts: dict[int, str] = {}
        # 需要翻译的部分
        need_translate_parts: dict[int, str] = {}
        position = 0
        for part in parts:
            if len(part) == 0:
                continue
            if Patterns.Skipped.search(part):
                skipped_parts.update({position: part})
            else:
                need_translate_parts.update({position: part})
            position += 1
        # 组装翻译
        return skipped_parts, need_translate_parts, position

    async def __preprocessing(self, src_file: Path) -> RawData:
        """
        预处理，读取文件，生成节点，将待翻译文本分块
        :param src_file:
        :return:
        """
        # 添加文件检查
        if not src_file.exists():
            raise FileNotFoundError(f"文件不存在: {src_file}")
        if not src_file.is_file():
            raise ValueError(f"不是有效的文件: {src_file}")
        src_lines = src_file.read_text(encoding="utf-8").splitlines()
        # 生成节点
        nodes = await self.__generate_nodes(src_lines)

        # 待翻译文本
        lines_to_translate = "".join(node.get_trans_buff() for node in nodes if node.get_trans_buff()).splitlines()
        # 将待翻译文本中的空行取出
        empty_line_position = [position for position, line in enumerate(lines_to_translate) if not line.strip()]
        lines_to_translate = [line for line in lines_to_translate if line.strip()]

        # 将文本分成多个和文本块，避免文本过长
        chunks, buff = [], []
        length = 0
        for line in lines_to_translate:
            buff.append(line)
            length += len(line)
            # 控制每次发送的数据量
            if length > 600:
                chunks.append(await self.__handle_chunk('\n'.join(buff) + '\n'))
                buff.clear()
                length = 0
        if length:
            chunks.append(await self.__handle_chunk('\n'.join(buff) + '\n'))

        # 统计需要翻译的字符数
        chars_count = sum([len("\n".join(parts.values())) for _, parts, _ in chunks])
        return RawData(nodes, chunks, empty_line_position, chars_count)

    # 建议添加错误处理


    async def parse(self):
        try:
            self.raw_data = await self.__preprocessing(self.src_file)
            return self.raw_data
        except Exception as e:
            print(f"解析错误: {e}")
            raise


class MDTranslate:
    __trans: Translator = Translator(5)
    def __init__(self, src_file: Path ):
        self.src_file = src_file
        self.target_files = []



    @staticmethod
    def __collect_files_to_translate(folders: Path) -> list[tuple[Path, list[str]]]:
        """
        按传入的文件夹列表收集需要翻译的文档和目标语言
        :param folders: 文件夹列表
        :return:
        """
        folders = [folders]
        files_to_translate = []
        for folder in folders:
            folder = Path(folder)
            if not folder.exists():
                logging.warning(f"{folder} does not exist, Skipped!!!")
                continue
            if folder.is_file():
                config.src_filenames = [folder.stem]
                folder = folder.parent

            # 每个文件夹下至少存在一个配置中的文件名
            if not any((Path(folder) / f"{src_filename}.md").exists() for src_filename in config.src_filenames):
                logging.warning(f"{folder} does not contain any file in src_filenames, Skipped!")
                continue

            for src_filename in config.src_filenames:
                src_file = Path(folder) / (src_filename + '.md')
                if not src_file.exists():
                    continue
                # 将要被翻译至的语言
                target_langs: list[str] = []
                for lang in config.target_langs:
                    target_file = Path(folder) / f'{src_filename}.{lang}.md'
                    if target_file.exists():
                        logging.warning(f"{shortedPath(target_file)} already exists, Skipped!")
                        continue
                    target_langs.append(lang)
                if len(target_langs):
                    files_to_translate.append((src_file, target_langs))
        return files_to_translate

    async def __translate_lines(self, raw_data: RawData, src_lang: str, target_lang: str, pbar: Pbar) -> str:
        """
        执行数据的拆分翻译组装
        """
        # 待翻译md文本
        translated_text = await self.__trans.translate_in_batch(raw_data, src_lang, target_lang, pbar)
        translated_lines = translated_text.splitlines()

        # 将翻译后的内容填充到节点中
        start_pos = 0
        nodes = copy.deepcopy(raw_data.nodes)
        for node in nodes:
            if node.trans_lines == 0:
                # 若有机器翻译警告的占位符，则填充警告内容
                if isinstance(node, TransparentNode) and node.value == "___HOLD_To_FILL_WARNING___":
                    node.value = f"\n> {config.warnings_mapping.get(target_lang, 'Warning Not Found')}\n"
                continue
            elif node.trans_lines == 1:
                node.value = translated_lines[start_pos]
            else:
                node.value = "\n".join(translated_lines[start_pos: start_pos + node.trans_lines])
            start_pos += node.trans_lines

        return "".join(node.compose() for node in nodes)
    async def __translate_to(self, src_file: Path, target_lang: str, global_pbar: tqdm, raw_data: RawData) -> None:
        """
        执行文件的读取、翻译、写入
        """
        target_file = src_file.parent / f'{src_file.stem}.{target_lang}.md'
        self.target_files.append(target_file)
        logging.info(f"Translating {shortedPath(src_file)} to {target_lang}")

        # 初始化当前线程的进度条
        local_pbar = tqdm(total=raw_data.chars_count, desc=shortedPath(target_file), unit='Chars',
                          unit_scale=True, leave=False, unit_divisor=1000)
        pbar = Pbar(global_pbar, local_pbar)
        try:
            translated_text = await self.__translate_lines(raw_data, config.src_language, target_lang, pbar)
            # translated_text = await self.__trans.translate_in_batch(raw_data, src_lang, target_lang, pbar)
            translated_lines = translated_text.splitlines()
            markdown_result, last_char = [], ""
            for translated_line in translated_lines:
                # 空行或者紧凑型语言则直接添加到结果中
                if (not translated_line.strip()) or target_lang in config.compact_langs:
                    markdown_result.append(translated_line)
                    continue
                # 非紧凑型语言则需要在特定的位置添加空格
                parts = Patterns.Expands.split(translated_line)
                line = "".join(expand_part(part, parts, position, last_char) for position, part in enumerate(parts))
                last_char = parts[-1][-1] if parts[-1] else last_char
                markdown_result.append(line)

            target_file.write_text('\n'.join(markdown_result), encoding="utf-8")
            logging.info(f"{shortedPath(src_file)} -> {target_lang} completed.")
            pbar.local_pbar_finished()
        except Exception as e:
            logging.error(f"Error occurred when translating {shortedPath(src_file)} to {target_lang}: {e}")
            pbar.local_pbar_finished(is_fail=True)
            # 重新抛出异常，让主线程捕获
            raise e

    async def translate(self,raw_data: RawData):
        try:

            for src_filename in config.src_filenames:
                src_file = self.src_file/ (src_filename + '.md')
                if not src_file.exists():
                    continue
            # 将要被翻译至的语言
            target_langs: list[str] = []
            # for lang, src_filename in zip(config.target_langs, config.src_filenames):
            #     target_file = self.src_file / f'{src_filename}.{lang}.md'
            #     print(target_file)
            #     # self.target_files.append(target_file)
            #     if target_file.exists():
            #         logging.warning(f"{shortedPath(target_file)} already exists, Skipped!")
            #         continue
            #     target_langs.append(lang)

            for lang in config.target_langs:
                target_langs.append(lang)


            global_pbar = tqdm(total=raw_data.chars_count, desc="Total Progress", unit='Chars',
                               unit_scale=True, unit_divisor=1000)
            await asyncio.gather(
                *[self.__translate_to(self.src_file, target_lang, global_pbar, raw_data) for target_lang in
                  target_langs])
            global_pbar.close()
        except Exception as e:
            logging.error(f"Error occurred when translating {shortedPath(self.src_file)}: {e}")
            raise

# 使用示例:
async def main():
    # md = MDAnalysis(Path("2.md"))
    # result = await md.parse()  # 异步调用解析
    document=MDTranslate(Path("c.md"))
    raw_data = await MDAnalysis(document.src_file).parse()
    # print(raw_data)
    await document.translate(raw_data)
    print(document.target_files)


if __name__ == "__main__":
    asyncio.run(main())
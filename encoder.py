import os, sys, time, asyncio, json, base64, shutil, traceback, ast, zipfile, inspect
import urllib.request

# 🚨 GUARANTEED EMERGENCY ALERT SYSTEM 🚨
_chat_id_str = os.getenv("CHAT_ID", "0").strip()
_raw_dump = os.getenv("DUMP_ID", "none")
_bot_token = os.getenv("BOT_TOKEN", "").strip()

# Safe Base64 Decoder to prevent decoding failures
def safe_b64_decode(b64_str):
    try:
        b64_str = b64_str.strip()
        b64_str = b64_str.replace('-', '+').replace('_', '/')
        padding = len(b64_str) % 4
        if padding == 2:
            b64_str += '=='
        elif padding == 3:
            b64_str += '='
        return base64.b64decode(b64_str).decode('utf-8')
    except Exception as e:
        print(f"B64 Helper Error: {e}")
        return "{}"

if ":::" in _raw_dump:
    parts = _raw_dump.split(":::")
    if len(parts) > 4:
        try:
            raw_set = parts[4]
            decoded_json_str = safe_b64_decode(raw_set)
            _settings = json.loads(decoded_json_str)
            _bot_token = _settings.get('__bot_token', _bot_token)
        except: pass

def emergency_alert(msg):
    if _bot_token and _chat_id_str != "0" and _chat_id_str != "none":
        try:
            url = f"https://api.telegram.org/bot{_bot_token}/sendMessage"
            payload = {"chat_id": _chat_id_str, "text": f"🚨 **GITHUB WORKER CRASHED:**\n\n`{msg[-2000:]}`", "parse_mode": "Markdown"}
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=10)
        except: pass

try:
    import pyrogram.utils

    def patched_get_peer_type(peer_id: int) -> str:
        val = str(peer_id)
        if val.startswith("-100"): return "channel"
        elif val.startswith("-"): return "chat"
        else: return "user"

    pyrogram.utils.get_peer_type = patched_get_peer_type

    from pyrogram import Client
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    API_ID_STR = os.getenv("API_ID", "0").strip()
    API_ID = int(API_ID_STR) if API_ID_STR.isdigit() else 0
    API_HASH = os.getenv("API_HASH", "").strip()
    BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

    TASK_TYPE = os.getenv("TASK_TYPE", "hardsub")
    VIDEO_ID = os.getenv("VIDEO_ID", "")
    SUB_ID = os.getenv("SUB_ID", "none")
    RENAME = os.getenv("RENAME", "output.mp4")
    CHAT_ID_STR = os.getenv("CHAT_ID", "0")
    CHAT_ID = int(CHAT_ID_STR) if CHAT_ID_STR.lstrip('-').isdigit() else 0
    THREAD_ID = os.getenv("THREAD_ID", "none")

    STATUS_MSG_ID = None
    RESOLUTION = "original"
    USER_SETTINGS = {}

    DUMP_ID = _raw_dump
    LOGO_ID = "none"
    USER_ID = ""

    if ":::" in _raw_dump:
        parts = _raw_dump.split(":::")
        DUMP_ID = parts[0]
        LOGO_ID = parts[1]
        if len(parts) > 2: STATUS_MSG_ID = parts[2]
        if len(parts) > 3: RESOLUTION = parts[3]
        if len(parts) > 4:
            try: 
                raw_set = parts[4]
                decoded_json_str = safe_b64_decode(raw_set)
                USER_SETTINGS = json.loads(decoded_json_str)
            except Exception as b64_err:
                print(f"Base64 Decode Exception: {b64_err}")
                try: USER_SETTINGS = ast.literal_eval(raw_set)
                except Exception as ast_err:
                    print(f"AST Decode Exception: {ast_err}")
        if len(parts) > 5:
            USER_ID = parts[5]

    # Override keys with the Payload sent from Hugging Face
    API_ID = int(USER_SETTINGS.get('__api_id', API_ID))
    API_HASH = USER_SETTINGS.get('__api_hash', API_HASH)
    BOT_TOKEN = USER_SETTINGS.get('__bot_token', BOT_TOKEN)

    if API_ID == 0 or not API_HASH or not BOT_TOKEN:
        raise ValueError("GitHub Credentials missing! Could not retrieve API_ID or BOT_TOKEN.")

    last_edit_time = 0

    def get_readable_time(seconds: int) -> str:
        result = ""
        (days, remainder) = divmod(seconds, 86400)
        if int(days) != 0: result += f"{int(days)}d "
        (hours, remainder) = divmod(remainder, 3600)
        if int(hours) != 0: result += f"{int(hours)}h "
        (minutes, seconds) = divmod(remainder, 60)
        if int(minutes) != 0: result += f"{int(minutes)}m "
        result += f"{int(seconds)} sec"
        return result.strip()

    async def get_duration(file_path):
        cmd =['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        stdout, _ = await proc.communicate()
        try: return float(stdout.decode().strip())
        except: return 0.0

    async def progress_bar(current, total, app, msg_id, action_text):
        global last_edit_time
        now = time.time()
        if now - last_edit_time > 5 or current == total:
            try:
                perc = (current / total) * 100 if total > 0 else 0
                bar_length = 10
                filled = int((perc / 100) * bar_length)
                bar = "▰" * filled + "▱" * (bar_length - filled)
                
                cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_cloud_task_cloud")]])
                text = (
                    f"『 ☁️ 𝗖 𝗟 𝗢 𝗨 𝗗   𝗡 𝗢 𝗗 𝗘 』\n"
                    f"╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
                    f"〚 𝗙𝗶𝗹𝗲 〛 `{RENAME}`\n"
                    f"〚 𝗧𝗮𝘀𝗸 〛 {action_text}\n"
                    f"〚 𝗟𝗼𝗮𝗱 〛 {bar} {perc:.1f}%\n"
                    f"〚 𝗦𝗶𝘇𝗲 〛 {current/(1024*1024):.1f} MB ⌁ {total/(1024*1024):.1f} MB\n"
                    f"╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
                    f"⚡Zoro 𝘌𝗻𝗴𝗶𝗻𝗲 𝘙𝘂𝗻𝗻𝗶𝗻𝗴"
                )
                await app.edit_message_text(CHAT_ID, msg_id, text, reply_markup=cancel_kb)
                last_edit_time = now
            except: pass

    async def send_error_to_telegram(app, msg_id, error_msg):
        try: await app.edit_message_text(CHAT_ID, msg_id, f"❌ **Cloud Worker Error:**\n\n`{error_msg[-1000:]}`")
        except: pass

    # Smart fallback media uploader
    async def safe_send_media(app, media_type, chat_id, thread, file_path, thumb_path, cap, has_thumb, progress_bar, msg_id, action_text):
        method = app.send_video if media_type == "video" else app.send_document
        sig = inspect.signature(method)
        
        kwargs = {
            "chat_id": chat_id,
            "caption": cap,
            "progress": progress_bar,
            "progress_args": (app, msg_id, action_text)
        }
        
        if thumb_path and os.path.exists(thumb_path) and has_thumb:
            kwargs["thumb"] = thumb_path
        else:
            kwargs["thumb"] = None

        if media_type == "video":
            kwargs["video"] = file_path
            if "supports_streaming" in sig.parameters:
                kwargs["supports_streaming"] = True
        else:
            kwargs["document"] = file_path
            
        if thread:
            if "message_thread_id" in sig.parameters:
                kwargs["message_thread_id"] = thread
            elif "reply_to_message_id" in sig.parameters:
                kwargs["reply_to_message_id"] = thread
                
        try:
            await method(**kwargs)
        except Exception as e:
            # Fallback to document if send_video fails unexpectedly (e.g. streaming/codec errors)
            if media_type == "video":
                print(f"send_video failed ({e}). Falling back to send_document...")
                if "video" in kwargs: 
                    del kwargs["video"]
                if "supports_streaming" in kwargs: 
                    del kwargs["supports_streaming"]
                
                kwargs["document"] = file_path
                doc_sig = inspect.signature(app.send_document)
                doc_kwargs = {k: v for k, v in kwargs.items() if k in doc_sig.parameters}
                await app.send_document(**doc_kwargs)
            else:
                raise e

    async def process_all():
        session_name = f"worker_{int(time.time() * 1000000)}"
        app = Client(session_name, api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
        try:
            await app.start()
        except Exception as auth_err:
            err_str = str(auth_err)
            if "FLOOD_WAIT" in err_str:
                import re as re_module
                match = re_module.search(r'(\d+)', err_str)
                wait_sec = int(match.group(1)) if match else 60
                await asyncio.sleep(wait_sec)
                await app.start()
            else:
                raise
        
        cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_cloud_task_cloud")]])
        msg_id = None
        
        if STATUS_MSG_ID and str(STATUS_MSG_ID).isdigit():
            msg_id = int(STATUS_MSG_ID)
            try: await app.edit_message_text(CHAT_ID, msg_id, f"⚙️ Worker Triggered: Preparing...\n📦 File: `{RENAME}`", reply_markup=cancel_kb)
            except:
                status_msg = await app.send_message(CHAT_ID, f"⚙️ Worker Triggered: Preparing...\n📦 File: `{RENAME}`", reply_markup=cancel_kb)
                msg_id = status_msg.id
        else:
            status_msg = await app.send_message(CHAT_ID, f"⚙️ Worker Triggered: Preparing...\n📦 File: `{RENAME}`", reply_markup=cancel_kb)
            msg_id = status_msg.id

        try:
            # == PHASE 1: DOWNLOAD ==
            try:
                orig_vid = await app.download_media(VIDEO_ID, progress=progress_bar, progress_args=(app, msg_id, "📥 Downloading Video"))
                if not orig_vid:
                    await send_error_to_telegram(app, msg_id, "Video download failed (Reference Expired). Please restart task.")
                    await app.stop()
                    return
                
                ext = os.path.splitext(orig_vid)[1]
                video_path = f"safe_vid{ext}"
                if os.path.exists(video_path): os.remove(video_path)
                shutil.move(orig_vid, video_path)
            except Exception as e:
                await send_error_to_telegram(app, msg_id, f"Video Download Error:\n{e}")
                await app.stop()
                return

            sub_path = None
            if TASK_TYPE == "hardsub" and SUB_ID != "none":
                try:
                    orig_sub = await app.download_media(SUB_ID, progress=progress_bar, progress_args=(app, msg_id, "📥 Downloading Subtitle"))
                    if orig_sub:
                        if orig_sub.lower().endswith('.zip') and zipfile.is_zipfile(orig_sub):
                            try:
                                with zipfile.ZipFile(orig_sub, 'r') as zip_ref:
                                    zip_ref.extractall("temp_zip")
                                for file in os.listdir("temp_zip"):
                                    if file.lower().endswith(('.ass', '.srt')):
                                        orig_sub = os.path.join("temp_zip", file)
                                        break
                            except: pass
                                        
                        ext = os.path.splitext(orig_sub)[1]
                        sub_path = f"safe_sub{ext}"
                        shutil.move(orig_sub, sub_path)
                except Exception as e:
                    await send_error_to_telegram(app, msg_id, f"Subtitle Download Error:\n{e}")
                    await app.stop()
                    return
                    
            logo_path = None
            wm_type = USER_SETTINGS.get('wm_type', 'image')
            wm_status = str(USER_SETTINGS.get('wm_status', 'ON')).upper()
            wm_opacity = float(USER_SETTINGS.get('wm_opacity', 1.0))
            wm_text = USER_SETTINGS.get('wm_text', '')
            wm_font_color = USER_SETTINGS.get('wm_font_color', 'white')

            if wm_status == 'ON':
                if wm_type == 'image' and LOGO_ID != "none":
                    try:
                        orig_logo = await app.download_media(LOGO_ID, progress=progress_bar, progress_args=(app, msg_id, "📥 Downloading Logo"))
                        if orig_logo:
                            ext = os.path.splitext(orig_logo)[1]
                            logo_path = f"safe_logo{ext}"
                            shutil.move(orig_logo, logo_path)
                    except: pass
                elif wm_type == 'text' and wm_text:
                    logo_path = None
            
            # == PHASE 2: ENCODE ==
            output = RENAME
            duration = await get_duration(video_path)
            os.makedirs("fonts", exist_ok=True)
            
            # Debug user settings payload in logs
            print(f"--- DEBUG: USER_SETTINGS RECEIVED ---")
            print(json.dumps(USER_SETTINGS, indent=4))
            print(f"-------------------------------------")

            # Parse user settings safely with default fallbacks
            crf = str(USER_SETTINGS.get('crf') or '30').split()[0]
            preset = str(USER_SETTINGS.get('preset') or 'veryfast').split()[0]
            codec = str(USER_SETTINGS.get('codec') or 'libx264').split()[0]
            audiocodec = str(USER_SETTINGS.get('audiocodec') or 'copy').split()[0]
            audio_bitrate = USER_SETTINGS.get('audio') or 'Original'
            tune = USER_SETTINGS.get('tune') or 'None'
            bit_depth = USER_SETTINGS.get('bit') or '8bit'
            fps = USER_SETTINGS.get('fps') or 'Original'
            
            v_args = ['-c:v', codec, '-preset', preset]
            if codec != 'copy':
                v_args.extend(['-crf', crf])
                if tune and tune != "None": v_args.extend(['-tune', str(tune).split()[0]])
                if bit_depth and '10bit' in str(bit_depth): v_args.extend(['-pix_fmt', 'yuv420p10le'])
                elif bit_depth and '8bit' in str(bit_depth): v_args.extend(['-pix_fmt', 'yuv420p'])
                else: v_args.extend(['-pix_fmt', 'yuv420p'])
                if fps and fps != "Original": v_args.extend(['-r', str(fps).split()[0]])
                
            a_args = ['-c:a', audiocodec]
            if audio_bitrate and audiocodec != 'copy' and audio_bitrate != 'Original':
                a_args.extend(['-b:a', str(audio_bitrate).split()[0]])

            meta_args = []
            for k, v in USER_SETTINGS.items():
                if k.startswith('meta_') and v:
                    tag = k[5:]
                    meta_args.extend(['-metadata', f'{tag}={v}'])

            vid_w = 1280
            try:
                cmd_w = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width', '-of', 'csv=s=x:p=0', video_path]
                p_w = await asyncio.create_subprocess_exec(*cmd_w, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
                out_w, _ = await p_w.communicate()
                if out_w: vid_w = int(out_w.decode().strip())
            except: pass

            wm_pos = USER_SETTINGS.get('wm_pos', 'tr')
            wm_size = int(USER_SETTINGS.get('wm_size', 15))
            alpha = max(0.1, min(1.0, wm_opacity))
            
            overlay_pos = {
                'tl': '10:10', 'tc': '(W-w)/2:10', 'tr': 'W-w-10:10',
                'ml': '10:(H-h)/2', 'c': '(W-w)/2:(H-h)/2', 'mr': 'W-w-10:(H-h)/2',
                'bl': '10:H-h-10', 'bc': '(W-w)/2:H-h-10', 'br': 'W-w-10:H-h-10'
            }
            drawtext_pos = {
                'tl': 'x=10:y=10', 'tc': 'x=(w-tw)/2:y=10', 'tr': 'x=w-tw-10:y=10',
                'ml': 'x=10:y=(h-th)/2', 'c': 'x=(w-tw)/2:y=(h-th)/2', 'mr': 'x=w-tw-10:y=(h-th)/2',
                'bl': 'x=10:y=h-th-10', 'bc': 'x=(w-tw)/2:y=h-th-10', 'br': 'x=w-tw-10:y=h-th-10'
            }
            use_wm = wm_status == 'ON' and ((wm_type == 'image' and logo_path) or (wm_type == 'text' and wm_text))

            def make_image_wm_filter(base_filter):
                lw = int(vid_w * (wm_size / 100.0))
                if lw % 2 != 0: lw += 1
                scale = f"{lw}:-1"
                pos = overlay_pos.get(wm_pos, 'W-w-10:10')
                if base_filter:
                    return f"[1:v]format=rgba,colorchannelmixer=aa={alpha},scale={scale}[logo];[0:v]{base_filter}[base];[base][logo]overlay={pos}:format=yuv420"
                return f"[1:v]format=rgba,colorchannelmixer=aa={alpha},scale={scale}[logo];[0:v][logo]overlay={pos}:format=yuv420"

            def make_text_wm_filter(base_filter):
                fs = max(12, int(24 * wm_size / 15))
                safe_text = wm_text.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace(",", "\\,")
                dt_pos = drawtext_pos.get(wm_pos, 'x=w-tw-10:y=10')
                font_file = ""
                for candidate in ["font/vtks mint.ttf", "font/Gakuran-Demo.otf", "fonts/HelveticaRoundedLTStd-BdCn.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
                    if os.path.exists(candidate):
                        font_file = f":fontfile='{os.path.abspath(candidate).replace(chr(92), '/')}'"
                        break
                dt = f"drawtext=text='{safe_text}'{font_file}:fontsize={fs}:fontcolor={wm_font_color}@{alpha}:{dt_pos}"
                if base_filter:
                    return f"{base_filter},{dt}"
                return dt

            faststart = ['-movflags', '+faststart']

            # Parse resolution from "480p" -> 480
            try:
                res_num = int(''.join(c for c in RESOLUTION if c.isdigit()))
                scale_vf = f"scale=-2:{res_num},"
            except:
                scale_vf = ""
            engine_name = "HARDSUB ENGINE"

            if TASK_TYPE == "hardsub":
                try:
                    res_num = int(''.join(c for c in RESOLUTION if c.isdigit()))
                    scale_prefix = f"scale=-2:{res_num},"
                except:
                    scale_prefix = ""
                fonts_dir = os.path.abspath("Fonts") if os.path.exists("Fonts") else os.path.abspath("fonts")
                fonts_dir_escaped = fonts_dir.replace("\\", "/").replace(":", "\\:")
                sub_filter_str = f"subtitles={os.path.basename(sub_path)}:fontsdir='{fonts_dir_escaped}'" if sub_path else ""
                if scale_prefix:
                    sub_filter_str = f"{scale_prefix}{sub_filter_str}" if sub_filter_str else scale_prefix[:-1]
                
                if use_wm:
                    if wm_type == 'image':
                        vf = make_image_wm_filter(sub_filter_str)
                        cmd = ['ffmpeg', '-y', '-i', video_path, '-i', logo_path, '-filter_complex', vf, '-map', '0:a?', '-sn'] + v_args + a_args + meta_args + faststart + ['-progress', 'pipe:1', output]
                    else:
                        vf = make_text_wm_filter(sub_filter_str)
                        cmd = ['ffmpeg', '-y', '-i', video_path, '-map', '0:v:0', '-map', '0:a?', '-sn', '-vf', vf] + v_args + a_args + meta_args + faststart + ['-progress', 'pipe:1', output]
                else:
                    if sub_filter_str:
                        cmd = ['ffmpeg', '-y', '-i', video_path, '-map', '0:v:0', '-map', '0:a?', '-sn', '-vf', sub_filter_str] + v_args + a_args + meta_args + faststart + ['-progress', 'pipe:1', output]
                    else:
                        cmd = ['ffmpeg', '-y', '-i', video_path, '-map', '0:v:0', '-map', '0:a?', '-sn'] + v_args + a_args + meta_args + faststart + ['-progress', 'pipe:1', output]
                engine_name = "HARDSUB ENGINE"
            else:
                vf_scale = f"scale=-2:{RESOLUTION}" if RESOLUTION != "original" else ""
                
                if use_wm:
                    if wm_type == 'image':
                        vf = make_image_wm_filter(vf_scale)
                        cmd = ['ffmpeg', '-y', '-i', video_path, '-i', logo_path, '-filter_complex', vf, '-map', '0:a?', '-sn'] + v_args + a_args + meta_args + faststart + ['-progress', 'pipe:1', output]
                    else:
                        vf = make_text_wm_filter(vf_scale)
                        cmd = ['ffmpeg', '-y', '-i', video_path, '-map', '0:v:0', '-map', '0:a?', '-sn', '-vf', vf] + v_args + a_args + meta_args + faststart + ['-progress', 'pipe:1', output]
                else:
                    if vf_scale:
                        cmd = ['ffmpeg', '-y', '-i', video_path, '-map', '0:v:0', '-map', '0:a?', '-sn', '-vf', vf_scale] + v_args + a_args + meta_args + faststart + ['-progress', 'pipe:1', output]
                    else:
                        cmd = ['ffmpeg', '-y', '-i', video_path, '-map', '0:v:0', '-map', '0:a?', '-sn'] + v_args + a_args + meta_args + faststart + ['-progress', 'pipe:1', output]
                engine_name = "COMPRESSION ENGINE"

            with open("ffmpeg_error.log", "w") as err_file:
                proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=err_file)
                
            start_time = time.time()
            last_up = 0

            while True:
                line = await proc.stdout.readline()
                if not line: break
                line = line.decode('utf-8').strip()
                if line.startswith('out_time_us='):
                    try:
                        time_str = line.split('=')[1]
                        if time_str.lower() == 'n/a': continue 
                        cur = int(time_str) / 1000000
                        now = time.time()
                        
                        if (now - last_up) > 10:
                            if duration > 0:
                                perc = min(100, (cur / duration) * 100)
                                elapsed = now - start_time
                                speed = cur / elapsed if elapsed > 0 else 0
                                eta = (duration - cur) / speed if speed > 0 else 0
                                bar_length = 10
                                filled = int((perc / 100) * bar_length)
                                bar = "▰" * filled + "▱" * (bar_length - filled)
                                prog_text = f"〚 𝗟𝗼𝗮𝗱 〛 {bar} {perc:.2f}%\n〚 𝗦𝗽𝗲𝗲𝗱 〛 {speed:.2f}x\n〚 𝗘𝗧𝗔 〛 ~{get_readable_time(eta)}"
                            else:
                                prog_text = f"〚 𝗟𝗼𝗮𝗱 〛 Processed: {get_readable_time(cur)}\n〚 𝗦𝗽𝗲𝗲𝗱 〛 Unknown"
                                
                            text = (
                                f"『 ☁️ 𝗖 𝗟 𝗢 𝗨 𝗗   𝗡 𝗢 𝗗 𝗘 』\n"
                                f"╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
                                f"〚 𝗙𝗶𝗹𝗲 〛 `{RENAME}`\n"
                                f"〚 𝗧𝗮𝘀𝗸 〛 Processing Frame...\n"
                                f"{prog_text}\n"
                                f"╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
                                f"⚡Zoro 𝘌𝗻𝗴𝗶𝗻𝗲 𝘙𝘂𝗻𝗻𝗶𝗻𝗴"
                            )
                            try: await app.edit_message_text(CHAT_ID, msg_id, text, reply_markup=cancel_kb)
                            except: pass
                            last_up = now
                    except: pass
                    
            await proc.wait()
            
            # == PHASE 3: UPLOAD ==
            if proc.returncode == 0 and os.path.exists(output):
                thumb_path = "thumb.jpg"
                thumb_data = USER_SETTINGS.get('__thumb_data')
                if thumb_data:
                    try:
                        with open(thumb_path, "wb") as tf:
                            tf.write(base64.b64decode(thumb_data))
                    except:
                        thumb_data = None
                if not thumb_data:
                    cmd_thumb = ['ffmpeg', '-y', '-ss', '00:00:05', '-i', output, '-vf', 'scale=320:-1', '-vframes', '1', thumb_path]
                    t_proc = await asyncio.create_subprocess_exec(*cmd_thumb, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                    await t_proc.wait()
                has_thumb = os.path.exists(thumb_path)

                if has_thumb:
                    ext = os.path.splitext(output)[1].lower()
                    final_out = output + ".tmp"
                    if ext == ".mkv":
                        cmd_cover = ['ffmpeg', '-y', '-i', output, '-attach', thumb_path, '-metadata:s:t', 'mimetype=image/jpeg', '-c', 'copy', final_out]
                    else:
                        # Count existing streams to place cover art at the right index
                        probe = await asyncio.create_subprocess_exec(
                            'ffprobe', '-v', 'error', '-show_entries', 'stream=index', '-of', 'csv=p=0', output,
                            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
                        )
                        p_out, _ = await probe.communicate()
                        stream_count = len(p_out.decode().strip().split('\n')) if p_out.decode().strip() else 0
                        cmd_cover = ['ffmpeg', '-y', '-i', output, '-i', thumb_path, '-map', '0', '-map', '1', '-c', 'copy', f'-disposition:{stream_count}', 'attached_pic', final_out]
                    cp = await asyncio.create_subprocess_exec(*cmd_cover, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                    await cp.wait()
                    if cp.returncode == 0 and os.path.exists(final_out):
                        os.remove(output)
                        os.rename(final_out, output)
                
                # Get upload format or fallback to video default
                up_format = USER_SETTINGS.get("upload_format") or USER_SETTINGS.get("upload") or "document"
                if str(up_format).lower().strip() not in ["video", "document"]:
                    up_format = "video"
                
                target_chat = int(DUMP_ID) if DUMP_ID != "none" else CHAT_ID
                thread = int(THREAD_ID) if THREAD_ID != "none" else None
                
                cap = f"✅ {TASK_TYPE.upper()} COMPLETE\n📦 File: `{RENAME}`"
                if USER_ID:
                    cap += f"\n👤 **Requested By:** [User](tg://user?id={USER_ID})"
                
                try:
                    if up_format == "video":
                        await safe_send_media(
                            app, "video", target_chat, thread, output, thumb_path, cap, 
                            has_thumb, progress_bar, msg_id, "📤 Uploading Video"
                        )
                    else:
                        await safe_send_media(
                            app, "document", target_chat, thread, output, thumb_path, cap, 
                            has_thumb, progress_bar, msg_id, "📤 Uploading Document"
                        )
                    
                    if target_chat != CHAT_ID:
                        tag_text = f"\n👤 [User](tg://user?id={USER_ID})" if USER_ID else ""
                        await app.send_message(CHAT_ID, f"{cap}\n\nFile successfully sent to your Dump Group!{tag_text}")
                        
                    await app.delete_messages(CHAT_ID, msg_id)
                except Exception as e:
                    await send_error_to_telegram(app, msg_id, f"Upload Error:\n{traceback.format_exc()}")
            else:
                err_msg = "Unknown Reason"
                if os.path.exists("ffmpeg_error.log"):
                    with open("ffmpeg_error.log", "r") as f:
                        err_msg = "".join(f.readlines()[-15:])[-1000:]
                await send_error_to_telegram(app, msg_id, f"FFmpeg Encode Failed:\n{err_msg}")

        except Exception as e:
            await send_error_to_telegram(app, msg_id, f"Fatal Worker Crash:\n{traceback.format_exc()}")
        finally:
            await app.stop()

    if __name__ == "__main__":
        loop = asyncio.get_event_loop()
        loop.run_until_complete(process_all())

except Exception as e:
    emergency_alert(traceback.format_exc())

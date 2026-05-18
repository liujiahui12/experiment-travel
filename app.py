from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from io import BytesIO
import traceback
from config import Config
from services.exif_service import EXIFService
from services.vision_service import VisionService
from services.location_service import LocationService
from services.text_service import TextService, CopyContext
from services.journal_service import JournalService

app = Flask(__name__)
app.config.from_object(Config)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

journal_service = JournalService()

STYLE_TEMPLATES = {
    'literary': {
        'name': '文艺清新',
        'prefix': '✨ ',
        'suffix': ' 💫',
        'date_format': '📅 {date}',
        'location_format': '📍 {location}'
    },
    'cute': {
        'name': '可爱俏皮',
        'prefix': '🌈 ',
        'suffix': ' 🎀',
        'date_format': '🎀 {date}',
        'location_format': '🎪 {location}'
    },
    'professional': {
        'name': '专业简洁',
        'prefix': '',
        'suffix': '',
        'date_format': '日期：{date}',
        'location_format': '地点：{location}'
    },
    'poetic': {
        'name': '诗意浪漫',
        'prefix': '🌸 ',
        'suffix': ' 🌺',
        'date_format': '时光流转 {date}',
        'location_format': '足迹印刻 {location}'
    }
}


def allowed_file(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in app.config['ALLOWED_EXTENSIONS']


def generate_travel_content(images_data, style, date=None, location='未知地点'):
    style_config = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES['literary'])
    content = []
    
    date_str = date if date else datetime.now().strftime('%Y年%m月%d日')
    
    content.append(f"{style_config['prefix']}旅行日记{style_config['suffix']}\n")
    content.append("=" * 50 + "\n")
    content.append(f"{style_config['date_format'].format(date=date_str)}\n")
    content.append(f"{style_config['location_format'].format(location=location)}\n")
    content.append("=" * 50 + "\n\n")
    
    for idx, img_data in enumerate(images_data, 1):
        content.append(f"\n{style_config['prefix']}第{idx}张照片{style_config['suffix']}\n")
        content.append(f"📍 {img_data.get('location', '未知地点')}\n")
        content.append(f"⏰ {img_data.get('capture_time', '未知时间')}\n")
        if img_data.get('generated_copy'):
            content.append(f"\n{img_data['generated_copy']}\n")
    
    content.append("\n\n" + "=" * 50)
    content.append(f"\n{style_config['prefix']}旅行感悟{style_config['suffix']}\n")
    content.append("每一次旅行都是一次心灵的洗礼，每一个瞬间都值得珍藏。\n")
    content.append("愿这份旅行记忆，成为时光里最美的印记。" + "\n")
    content.append("=" * 50 + "\n")
    
    return ''.join(content)

def generate_timeline(images_data, style):
    style_config = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES['literary'])
    timeline = []
    
    for idx, img_data in enumerate(images_data, 1):
        time = img_data.get('capture_time', datetime.now().strftime('%Y年%m月%d日 %H:%M'))
        timeline.append({
            'time': time,
            'index': idx,
            'image': img_data.get('filename', ''),
            'location': img_data.get('location', '未知地点'),
            'description': f"{style_config['prefix']}第{idx}站{style_config['suffix']}"
        })
    
    return timeline

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/')
def index():
    return render_template('index.html', styles=STYLE_TEMPLATES)


@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'message': '未选择文件'})
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'message': '未选择文件'})
        
        style = request.form.get('style', 'literary')
        
        images_data = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
                unique_filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                
                result = process_image(filepath, style)
                if result.get('success'):
                    img_data = result.get('data', {})
                    img_data['filename'] = unique_filename
                    images_data.append(img_data)
        
        if not images_data:
            return jsonify({'success': False, 'message': '没有有效的图片文件'})
        
        first_img = images_data[0]
        date = first_img.get('capture_time', datetime.now().strftime('%Y年%m月%d日'))
        if ' ' in date:
            date = date.split(' ')[0]
        
        first_location = first_img.get('location', '未知地点')
        if first_location != '未知地点':
            if '省' in first_location and '市' in first_location:
                province_idx = first_location.index('省')
                city_idx = first_location.index('市')
                if province_idx < city_idx:
                    location = first_location[:city_idx + 1]
                else:
                    location = first_location
            else:
                location = first_location
        else:
            location = '未知地点'
        
        content = generate_travel_content(images_data, style, date, location)
        timeline = generate_timeline(images_data, style)
        
        return jsonify({
            'success': True,
            'content': content,
            'timeline': timeline,
            'style': style,
            'images_data': images_data,
            'date': date,
            'location': location
        })
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'处理失败: {str(e)}'})


def process_image(image_path, style="literary"):
    exif_service = EXIFService()
    vision_service = VisionService()
    location_service = LocationService()
    text_service = TextService()
    
    exif_info = exif_service.parse_exif(image_path)
    
    vision_result = vision_service.analyze_image(image_path)
    
    location_info = None
    poi_list = []
    location_str = "未知地点"
    
    if exif_info.has_gps and exif_info.gps_coordinate:
        gps = exif_info.gps_coordinate
        location_info = location_service.reverse_geocoding(gps.latitude, gps.longitude)
        
        if location_info.address:
            location_str = location_info.address
            poi_list = location_service.search_poi("景点", gps.latitude, gps.longitude)
        
        poi_data = [{
            'name': p.name, 
            'address': p.address, 
            'distance': p.distance,
            'description': p.description,
            'best_time': p.best_time,
            'tips': p.tips
        } for p in poi_list[:5]]
    else:
        poi_data = []
    
    capture_time_str = "未知时间"
    if exif_info.capture_time:
        capture_time_str = exif_info.capture_time.strftime("%Y年%m月%d日 %H:%M")
    
    if vision_result.success and vision_result.content:
        copy_context = CopyContext(
            image_content=vision_result.content,
            location=location_str,
            capture_time=capture_time_str,
            poi_list=poi_data
        )
        
        copy_result = text_service.generate_copy(copy_context, style)
        
        if copy_result.success:
            generated_copy = copy_result.content
        else:
            generated_copy = f"""✨ 探索之旅开启啦！

今天来到了{location_str}，这里的环境真的很不错呢！{'附近有' + poi_data[0]['name'] + '等热门景点可以打卡，' if poi_data else ''}适合周末放松，也适合拍照记录美好时光。

📸 推荐大家来这里感受一下，记得带上好心情！

{'📍 ' + location_str if location_str != '未知地点' else ''}
#旅行打卡 #探索美好"""
    else:
        generated_copy = f"无法生成文案: {vision_result.message}"
    
    return {
        'success': True,
        'data': {
            'image_content': vision_result.content if vision_result.success else vision_result.message,
            'location': location_str,
            'capture_time': capture_time_str,
            'has_gps': exif_info.has_gps,
            'gps_message': exif_info.message,
            'poi_list': poi_data,
            'generated_copy': generated_copy
        }
    }


@app.route('/result')
def result():
    return render_template('result.html', styles=STYLE_TEMPLATES)

@app.route('/change_style', methods=['POST'])
def change_style():
    try:
        data = request.get_json()
        images_data = data.get('images_data', [])
        style = data.get('style', 'literary')
        date = data.get('date', '')
        location = data.get('location', '未知地点')
        
        text_service = TextService()
        location_service = LocationService()
        
        for img_data in images_data:
            image_content = img_data.get('image_content', '')
            capture_time = img_data.get('capture_time', '')
            img_location = img_data.get('location', '未知地点')
            poi_list = img_data.get('poi_list', [])
            
            if image_content:
                copy_context = CopyContext(
                    image_content=image_content,
                    location=img_location,
                    capture_time=capture_time,
                    poi_list=poi_list
                )
                
                copy_result = text_service.generate_copy(copy_context, style)
                
                if copy_result.success:
                    img_data['generated_copy'] = copy_result.content
                else:
                    img_data['generated_copy'] = f"无法生成文案: {copy_result.message}"
        
        content = generate_travel_content(images_data, style, date, location)
        timeline = generate_timeline(images_data, style)
        
        return jsonify({
            'success': True,
            'content': content,
            'timeline': timeline,
            'images_data': images_data
        })
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'切换风格失败: {str(e)}'})

@app.route('/export/<format_type>', methods=['POST'])
def export_content(format_type):
    try:
        data = request.get_json()
        content = data.get('content', '')
        date = data.get('date', datetime.now().strftime('%Y%m%d'))
        
        if format_type == 'txt':
            output = BytesIO()
            output.write(content.encode('utf-8'))
            output.seek(0)
            return send_file(
                output,
                mimetype='text/plain',
                as_attachment=True,
                download_name=f'旅行日记_{date}.txt'
            )
        
        elif format_type == 'pdf':
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                
                output = BytesIO()
                doc = SimpleDocTemplate(output, pagesize=A4)
                styles = getSampleStyleSheet()
                
                try:
                    pdfmetrics.registerFont(TTFont('SimSun', 'simsun.ttc'))
                    chinese_style = ParagraphStyle(
                        'Chinese',
                        parent=styles['Normal'],
                        fontName='SimSun',
                        fontSize=12,
                        leading=18
                    )
                except:
                    chinese_style = styles['Normal']
                
                story = []
                for line in content.split('\n'):
                    if line.strip():
                        story.append(Paragraph(line, chinese_style))
                        story.append(Spacer(1, 6))
                
                doc.build(story)
                output.seek(0)
                return send_file(
                    output,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=f'旅行日记_{date}.pdf'
                )
            except ImportError:
                return jsonify({'success': False, 'message': 'PDF导出需要安装reportlab库: pip install reportlab'})
        
        elif format_type == 'docx':
            try:
                from docx import Document
                
                doc = Document()
                for line in content.split('\n'):
                    if line.strip():
                        doc.add_paragraph(line)
                
                output = BytesIO()
                doc.save(output)
                output.seek(0)
                return send_file(
                    output,
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    as_attachment=True,
                    download_name=f'旅行日记_{date}.docx'
                )
            except ImportError:
                return jsonify({'success': False, 'message': 'DOCX导出需要安装python-docx库: pip install python-docx'})
        
        else:
            return jsonify({'success': False, 'message': '不支持的导出格式'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'})


@app.route('/journals')
def journals():
    return render_template('journals.html', styles=STYLE_TEMPLATES)


@app.route('/journals/<journal_id>')
def journal_detail(journal_id):
    return render_template('journal_detail.html', styles=STYLE_TEMPLATES, journal_id=journal_id)


@app.route('/api/journals/save', methods=['POST'])
def api_save_journal():
    try:
        data = request.get_json()
        
        result = journal_service.save_journal(
            capture_date=data.get('date', ''),
            location=data.get('location', ''),
            content=data.get('content', ''),
            style=data.get('style', 'literary'),
            images_data=data.get('images_data', []),
            timeline=data.get('timeline', []),
            poi_list=data.get('poi_list', [])
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'保存失败: {str(e)}'})


@app.route('/api/journals', methods=['GET'])
def api_get_journals():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        result = journal_service.get_journals(page, per_page)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'查询失败: {str(e)}'})


@app.route('/api/journals/<journal_id>', methods=['GET'])
def api_get_journal(journal_id):
    try:
        result = journal_service.get_journal_detail(journal_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'查询失败: {str(e)}'})


@app.route('/api/journals/<journal_id>', methods=['DELETE'])
def api_delete_journal(journal_id):
    try:
        result = journal_service.delete_journal(journal_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})


@app.route('/api/journals/search', methods=['GET'])
def api_search_journals():
    try:
        location = request.args.get('location', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        result = journal_service.search_journals(
            location=location if location else None,
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'搜索失败: {str(e)}'})


@app.errorhandler(413)
def too_large(e):
    return jsonify({'success': False, 'message': '文件太大，最大支持16MB'}), 413


@app.errorhandler(500)
def internal_error(e):
    return jsonify({'success': False, 'message': '服务器内部错误'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

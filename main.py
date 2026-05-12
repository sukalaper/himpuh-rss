from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import requests
from datetime import datetime, timezone, timedelta
import re

# 1. Scraping Data
url = "https://himpuh.or.id/blog/kategori/2/berita"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

judul_divs = soup.find_all('div', class_='judul')
articles = []

month_map = {
    'januari': 'January', 'februari': 'February', 'maret': 'March',
    'april': 'April', 'mei': 'May', 'juni': 'June',
    'juli': 'July', 'agustus': 'August', 'september': 'September',
    'oktober': 'October', 'november': 'November', 'desember': 'December'
}

for i, judul_div in enumerate(judul_divs):
    title_link = judul_div.find('a')
    if not title_link: continue
    
    title = title_link.text.strip()
    article_link = title_link.get('href', url)
    if article_link.startswith('/'):
        article_link = 'https://himpuh.or.id' + article_link
    
    parent = judul_div.parent
    content_elem = parent.find('div', class_='intro mb5') if parent else None
    content = content_elem.text.strip() if content_elem else "No content found"
    
    thumbnail = parent.find('div', class_='thumbnail') if parent else None
    image_url = None
    if thumbnail and 'data-origin' in thumbnail.attrs:
        image_url = thumbnail['data-origin']
    
    waktu_posting = parent.find('div', class_='waktu-posting') if parent else None
    published_date = None
    if waktu_posting:
        waktu_text = waktu_posting.get_text()
        match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4}),\s*(\d{1,2}):(\d{2}):(\d{2})', waktu_text)
        if match:
            day, month_id, year, hour, minute, second = match.groups()
            month_en = month_map.get(month_id.lower(), month_id)
            try:
                date_str = f"{day} {month_en} {year} {hour}:{minute}:{second}"
                published_date = datetime.strptime(date_str, "%d %B %Y %H:%M:%S")
                published_date = published_date.replace(tzinfo=timezone(timedelta(hours=7)))
            except: published_date = None
    
    articles.append({
        'title': title,
        'link': article_link,
        'content': content,
        'image': image_url,
        'published_date': published_date
    })

# Sort & Limit
articles.sort(key=lambda x: x['published_date'] if x['published_date'] else datetime.min(tzinfo=timezone.utc), reverse=True)
articles = articles[:10] # Ambil 10 biar lebih asik

# 2. Generate RSS Feed
if articles:
    fg = FeedGenerator()
    fg.title("Himpuh Blog Feed")
    fg.link(href=url, rel='alternate')
    # Self link buat validator
    fg.link(href="https://raw.githubusercontent.com/sukalaper/himpuh-rss/main/output.xml", rel='self')
    fg.description("A feed of Himpuh blog posts")
    fg.language('id')
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in articles:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['content'])
        # GUID biar gak duplikat di Reader
        entry.guid(item['link'], permalink=True)
        
        if item['image']:
            entry.enclosure(url=item['image'], length='0', type='image/webp')
        
        if item['published_date']:
            entry.pubDate(item['published_date'])
        else:
            entry.pubDate(datetime.now(timezone.utc))

    # 3. Save with proper header
    try:
        rss_feed = fg.rss_str(pretty=True)
        with open('output.xml', 'wb') as f:
            f.write(rss_feed)
        print(f"Success! {len(articles)} items saved to output.xml")
    except Exception as e:
        print(f"Error saving file: {e}")
        

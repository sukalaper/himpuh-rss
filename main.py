import requests
import re
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone, timedelta

def scrape_himpuh():
    url = "https://himpuh.or.id/blog/kategori/2/berita"
    # User-Agent biar gak dianggap bot jahat
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"Gagal narik data: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    judul_divs = soup.find_all('div', class_='judul')
    articles = []

    # Mapping bulan Indonesia ke Inggris buat parsing datetime
    month_map = {
        'januari': 'January', 'februari': 'February', 'maret': 'March',
        'april': 'April', 'mei': 'May', 'juni': 'June',
        'juli': 'July', 'agustus': 'August', 'september': 'September',
        'oktober': 'October', 'november': 'November', 'desember': 'December'
    }

    for i, judul_div in enumerate(judul_divs):
        title_link = judul_div.find('a')
        if not title_link:
            continue
        
        title = title_link.text.strip()
        article_link = title_link.get('href', url)
        if article_link.startswith('/'):
            article_link = 'https://himpuh.or.id' + article_link
        
        # Ambil ringkasan berita
        parent = judul_div.parent
        content_elem = parent.find('div', class_='intro mb5') if parent else None
        content = content_elem.text.strip() if content_elem else "No content found"
        
        # Ambil gambar thumbnail
        thumbnail = parent.find('div', class_='thumbnail') if parent else None
        image_url = None
        if thumbnail and 'data-origin' in thumbnail.attrs:
            image_url = thumbnail['data-origin']
        
        # Ambil dan parsing tanggal posting
        waktu_posting = parent.find('div', class_='waktu-posting') if parent else None
        published_date = None
        if waktu_posting:
            waktu_text = waktu_posting.get_text()
            # Regex buat ambil format: 12 Mei 2026, 10:30:28
            match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4}),\s*(\d{1,2}):(\d{2}):(\d{2})', waktu_text)
            if match:
                day, month_id, year, hour, minute, second = match.groups()
                month_en = month_map.get(month_id.lower(), month_id)
                try:
                    date_str = f"{day} {month_en} {year} {hour}:{minute}:{second}"
                    published_date = datetime.strptime(date_str, "%d %B %Y %H:%M:%S")
                    # Set ke timezone Jakarta (UTC+7)
                    published_date = published_date.replace(tzinfo=timezone(timedelta(hours=7)))
                except:
                    published_date = None
        
        articles.append({
            'title': title,
            'link': article_link,
            'content': content,
            'image': image_url,
            'published_date': published_date
        })

    # Sort berdasarkan tanggal terbaru
    articles.sort(key=lambda x: x['published_date'] if x['published_date'] else datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return articles[:10] # Ambil 10 berita terbaru

def generate_rss(articles):
    if not articles:
        print("Gak ada artikel buat dibikin feed.")
        return

    fg = FeedGenerator()
    fg.title("Himpuh Blog Feed")
    fg.link(href="https://himpuh.or.id/blog/kategori/2/berita", rel='alternate')
    
    # PERBAIKAN: Self link supaya validator ijo
    fg.link(href="https://raw.githubusercontent.com/sukalaper/himpuh-rss/main/output.xml", rel='self')
    
    fg.description("Feed berita resmi dari Himpuh (Himpunan Penyelenggara Umrah dan Haji)")
    fg.language('id')
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in articles:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        
        # PERBAIKAN: Tambah GUID supaya gak duplikat di RSS Reader
        entry.guid(item['link'], permalink=True)
        
        entry.description(item['content'])
        
        # Tambah gambar
        if item['image']:
            entry.enclosure(url=item['image'], length='0', type='image/webp')
        
        # Set tanggal publikasi
        if item['published_date']:
            entry.pubDate(item['published_date'])
        else:
            entry.pubDate(datetime.now(timezone.utc))

    # Simpan file dengan header XML yang bener
    try:
        rss_feed = fg.rss_str(pretty=True)
        with open('output.xml', 'wb') as f:
            f.write(rss_feed)
        print(f"Mantap! output.xml berhasil diupdate dengan {len(articles)} berita.")
    except Exception as e:
        print(f"Gagal pas nyimpen file: {e}")

if __name__ == "__main__":
    berita = scrape_himpuh()
    generate_rss(berita)
    

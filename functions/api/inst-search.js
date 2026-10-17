// Adapted from Rekasong's YouTube MR search; upstream HTML may change.
export async function onRequestGet({request}) {
  const reply=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json; charset=utf-8','Access-Control-Allow-Origin':'*','Cache-Control':status===200?'public, max-age=120':'no-store'}});
  const q=new URL(request.url).searchParams.get('q')?.trim();
  if(!q||q.length>200)return reply({error:'곡명을 200자 이내로 입력하세요.'},400);
  try{
    const query=`${q} (inst OR "off vocal" OR instrumental OR mr OR karaoke OR 노래방)`;
    const response=await fetch(`https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`,{headers:{'User-Agent':'Mozilla/5.0','Accept-Language':'ko-KR,ko;q=0.9,en;q=0.8'},signal:AbortSignal.timeout(10000)});
    if(!response.ok)throw Error('upstream');
    const html=await response.text(),match=html.match(/(?:var ytInitialData\s*=\s*|window\["ytInitialData"\]\s*=\s*)(\{.*?\});\s*<\/script>/s);
    if(!match)throw Error('format');
    const sections=JSON.parse(match[1]).contents?.twoColumnSearchResultsRenderer?.primaryContents?.sectionListRenderer?.contents;
    if(!Array.isArray(sections))throw Error('format');
    const videos=[],seen=new Set();
    for(const section of sections)for(const item of section.itemSectionRenderer?.contents||[]){
      const v=item.videoRenderer;if(!v||!/^[-\w]{11}$/.test(v.videoId)||seen.has(v.videoId))continue;
      seen.add(v.videoId);videos.push({id:v.videoId,title:v.title?.runs?.map(r=>r.text).join('')||v.title?.simpleText||'YouTube 영상',channelTitle:v.ownerText?.runs?.map(r=>r.text).join('')||'',durationText:v.lengthText?.simpleText||''});
    }
    const priority=title=>/(off[\s_-]*vocals?|\binst(?:rumental)?\b|(?:^|[^a-z])mr(?:$|[^a-z])|インスト|伴奏)/i.test(title)?2:/(반주|노래방|karaoke|\btj\b|\bky\b|금영|태진|カラオケ)/i.test(title)?1:0;
    videos.sort((a,b)=>priority(b.title)-priority(a.title));
    return reply(videos.slice(0,10));
  }catch{return reply({error:'YouTube 검색을 불러오지 못했습니다. 새 탭 검색을 이용하거나 주소를 붙여넣으세요.'},502);}
}

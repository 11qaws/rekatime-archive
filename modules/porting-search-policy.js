// One shared exclusion policy for search API and visible results.
const RekaInstSearchAllowed = video => {
  const text=[video.title,video.channelTitle].filter(Boolean).join(' ').normalize('NFKC').toLowerCase().replace(/[\s\p{P}\p{S}\p{Cf}]/gu,'');
  return !/(mc무현|mc무혐|mc재앙|mc재명|mc석열|mc유신|mc대중|노무현|문재인|윤석열|이재명|박근혜|박정희|이명박|김대중|김영삼|전두환|노태우|이승만|김일성|김정일|김정은|수령님|장군님|축지법|정치|정당|국민의힘|더불어민주당|새누리당|조선로동당|탄핵|대선|총선|일베|노알라|응디시티|봉하반점)/i.test(text);
};
if(typeof module!=='undefined')module.exports=RekaInstSearchAllowed;

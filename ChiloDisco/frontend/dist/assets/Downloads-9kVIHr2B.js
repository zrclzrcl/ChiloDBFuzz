import{h as o,_ as i,c as d,d as a,F as r,e as p,f as s,p as h,x as u,t as l,m as y,y as _,u as m,D as k}from"./index-DKzMqUOh.js";/**
 * @license lucide-vue-next v0.555.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const w=o("archive",[["rect",{width:"20",height:"5",x:"2",y:"3",rx:"1",key:"1wp1u1"}],["path",{d:"M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8",key:"1s80jp"}],["path",{d:"M10 12h4",key:"a56b0p"}]]);/**
 * @license lucide-vue-next v0.555.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const c=o("database",[["ellipse",{cx:"12",cy:"5",rx:"9",ry:"3",key:"msslwz"}],["path",{d:"M3 5V19A9 3 0 0 0 21 19V5",key:"1wlel7"}],["path",{d:"M3 12A9 3 0 0 0 21 12",key:"mv7ke4"}]]);/**
 * @license lucide-vue-next v0.555.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const f=o("file-text",[["path",{d:"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z",key:"1oefj6"}],["path",{d:"M14 2v5a1 1 0 0 0 1 1h5",key:"wfsgrz"}],["path",{d:"M10 9H8",key:"b1mrlr"}],["path",{d:"M16 13H8",key:"t4e002"}],["path",{d:"M16 17H8",key:"z1uh3a"}]]),v={class:"page-downloads"},b={class:"downloads-grid"},x={class:"icon-box"},M={class:"info"},B=["href"],V={__name:"Downloads",setup(g){const n=[{id:1,title:"Bitmap (Sum)",desc:"累计命中次数统计",url:"/api/download/bitmap?type=sum",icon:c},{id:2,title:"Bitmap (Bool)",desc:"覆盖率布尔位图",url:"/api/download/bitmap?type=bool",icon:c},{id:3,title:"Bitmap (All)",desc:"所有位图数据打包",url:"/api/download/bitmap/all",icon:w},{id:4,title:"Fuzz Stats",desc:"模糊测试统计数据 (CSV)",url:"/api/plot?format=csv",icon:f}];return(D,t)=>(s(),d("div",v,[t[1]||(t[1]=a("header",{class:"page-header"},[a("h1",null,"结果下载")],-1)),a("div",b,[(s(),d(r,null,p(n,e=>a("div",{class:"card download-card",key:e.id},[a("div",x,[(s(),h(u(e.icon)))]),a("div",M,[a("h3",null,l(e.title),1),a("p",null,l(e.desc),1)]),a("a",{href:e.url,class:"btn-download",download:""},[y(m(k),{class:"btn-icon"}),t[0]||(t[0]=_(" 下载 ",-1))],8,B)])),64))])]))}},A=i(V,[["__scopeId","data-v-d059fb4c"]]);export{A as default};

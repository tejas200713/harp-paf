export const demoLabel = 'Illustrative — not measured';
export const jobs = [
  { jobId: 'HPA-2026-041', filenames: ['matrix.cpp', 'stencil.c'], status: 'Completed', createdAt: '2026-10-12 14:32', completedAt: '2026-10-12 14:34', progressStage: 8 },
  { jobId: 'HPA-2026-038', filenames: ['graph.hpp'], status: 'Completed', createdAt: '2026-10-11 10:18', completedAt: '2026-10-11 10:20', progressStage: 8 },
  { jobId: 'HPA-2026-035', filenames: ['sort.cpp', 'reduce.cpp'], status: 'Failed', createdAt: '2026-10-09 16:05', completedAt: '2026-10-09 16:05', progressStage: 1, errorMessage: 'Illustrative validation failure' }
];
export const summary = { harpMakespan: 8.42, baselineMakespan: 10.0, speedup: 1.19, runtimeReductionPercent: 15.8, worstTaskSlowdown: 0.12, repetitions: 30, meanRuntime: 8.42, medianRuntime: 8.37, standardDeviation: 0.31, confidenceInterval: [8.31, 8.53], schedulingOverhead: 0.08 };
export const makespan = [{ name: 'Linux Default', value: 10.0 }, { name: 'Random Pairing', value: 9.61 }, { name: 'Port-Only', value: 9.22 }, { name: 'HARP-PAF', value: 8.42 }];
export const tasks = [
  { id: 'T01', name: 'Matrix Multiply', solo: 4.6, coRun: 5.0, slowdown: .09, instructions: '2.41 B', cycles: '3.08 B', ipc: 1.27, cpi: .79, cacheMisses: '18.2 M', llcMpki: 7.5, branchMisses: '1.4 M', branchMpki: .58, memoryBandwidth: '12.4 GB/s', frontStall: '8.2%', backStall: '21.4%', phases: [{t:0,memory:8,resource:40,front:9,back:19},{t:1,memory:10,resource:54,front:8,back:24},{t:2,memory:14,resource:68,front:7,back:28},{t:3,memory:11,resource:52,front:8,back:22},{t:4,memory:9,resource:43,front:10,back:17}] },
  { id: 'T02', name: 'Stencil Update', solo: 3.8, coRun: 4.0, slowdown: .05, instructions: '1.87 B', cycles: '2.15 B', ipc: 1.63, cpi: .61, cacheMisses: '9.7 M', llcMpki: 5.2, branchMisses: '0.8 M', branchMpki: .43, memoryBandwidth: '18.1 GB/s', frontStall: '5.9%', backStall: '34.1%', phases: [{t:0,memory:12,resource:32,front:7,back:25},{t:1,memory:16,resource:41,front:6,back:31},{t:2,memory:22,resource:38,front:5,back:36},{t:3,memory:19,resource:36,front:6,back:32},{t:4,memory:15,resource:34,front:7,back:26}] },
  { id: 'T03', name: 'Graph Traversal', solo: 5.1, coRun: 5.7, slowdown: .12, instructions: '3.12 B', cycles: '4.91 B', ipc: .64, cpi: 1.56, cacheMisses: '41.3 M', llcMpki: 13.2, branchMisses: '12.1 M', branchMpki: 3.88, memoryBandwidth: null, frontStall: '18.4%', backStall: '39.7%', phases: null },
  { id: 'T04', name: 'Image Filter', solo: 2.9, coRun: 3.0, slowdown: .03, instructions: '1.24 B', cycles: '1.52 B', ipc: .82, cpi: 1.22, cacheMisses: '7.1 M', llcMpki: 5.7, branchMisses: '0.6 M', branchMpki: .48, memoryBandwidth: '6.8 GB/s', frontStall: null, backStall: '16.2%', phases: null }
];
export const pairs = [
  { taskA:'T01',taskB:'T02',core:0,cpus:'0 / 1',resourceContention:.32,cachePressure:.24,bandwidthOverlap:.46,stallOverlap:.18,speculationPenalty:.12,complementarity:.72,predictedSlowdown:.08,uncertainty:.04,finalPairCost:.21 },
  { taskA:'T01',taskB:'T03',core:0,cpus:'0 / 1',resourceContention:.71,cachePressure:.68,bandwidthOverlap:.57,stallOverlap:.62,speculationPenalty:.31,complementarity:.22,predictedSlowdown:.24,uncertainty:.08,finalPairCost:.49 },
  { taskA:'T01',taskB:'T04',core:1,cpus:'2 / 3',resourceContention:.41,cachePressure:.37,bandwidthOverlap:.28,stallOverlap:.24,speculationPenalty:.18,complementarity:.66,predictedSlowdown:.09,uncertainty:.04,finalPairCost:.23 },
  { taskA:'T02',taskB:'T03',core:1,cpus:'2 / 3',resourceContention:.54,cachePressure:.61,bandwidthOverlap:.78,stallOverlap:.48,speculationPenalty:.26,complementarity:.39,predictedSlowdown:.19,uncertainty:.07,finalPairCost:.41 },
  { taskA:'T02',taskB:'T04',core:0,cpus:'0 / 1',resourceContention:.29,cachePressure:.33,bandwidthOverlap:.31,stallOverlap:.22,speculationPenalty:.14,complementarity:.70,predictedSlowdown:.07,uncertainty:.03,finalPairCost:.18 },
  { taskA:'T03',taskB:'T04',core:1,cpus:'2 / 3',resourceContention:.38,cachePressure:.46,bandwidthOverlap:.52,stallOverlap:.41,speculationPenalty:.21,complementarity:.55,predictedSlowdown:.13,uncertainty:.06,finalPairCost:.31 }
];
export const predictions = [];
export const runDistribution = [{name:'Linux Default',min:9.4,q1:9.7,median:10,max:10.5},{name:'HARP-PAF',min:7.9,q1:8.2,median:8.4,max:9.0}];

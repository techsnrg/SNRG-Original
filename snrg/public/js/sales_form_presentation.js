// Presentation only. Prepare grid columns before native rendering; never move controls.
(() => {
 const specs=[['item_code',115,'Code'],['item_name',260,'Item Name'],['qty',70,'Qty'],['uom',65,'UOM'],['price_list_rate',100,'List Rate'],['discount_percentage',85,'Discount %'],['rate',100,'Rate'],['amount',120,'Amount'],['actual_qty',80,'Stock Qty']];
 const prepare=frm=>{
  const grid=frm.fields_dict.items?.grid;if(!grid)return;
  grid.setup_fields();
  const cols=specs.map(([name,width,label])=>{
   const f=grid.fields_map[name];if(!f||f.hidden||!frm.get_perm(f.permlevel,'read'))return null;
   return [Object.assign({},f,{label,width,in_list_view:1}),width];
  }).filter(Boolean);
  grid.visible_columns=cols;grid.user_defined_columns=cols.map(c=>c[0]);
  // Navigation can reuse rows from the previous document. Data stays in frm.doc.
  if(grid.wrapper){grid.wrapper.find('.grid-body .grid-row').remove();grid.grid_rows=[];}
 };
 const decorate=frm=>{
  const grid=frm.fields_dict.items?.grid;if(!grid)return;
  const rowLabel=row=>{if(row?.grid===grid)row.wrapper.find('[data-fieldname="item_code"] .static-area a').first().text(row.doc.item_code||'');};
  const gridLabels=()=>{
   specs.forEach(([name,width,label])=>grid.wrapper.find('.grid-heading-row [data-fieldname="'+name+'"] > .static-area').text(label));
   (grid.grid_rows||[]).forEach(rowLabel);
  };
  frm.page.wrapper.off('grid-row-render.snrg-sales-presentation').on('grid-row-render.snrg-sales-presentation',(e,row)=>rowLabel(row));
  grid.wrapper.off('change.snrg-sales-presentation').on('change.snrg-sales-presentation',gridLabels);
  gridLabels();
  const label=(name,text)=>frm.fields_dict[name]?.$wrapper.find('.control-label').first().text(text);
  label('total','Item Total');label('net_total','Taxable Total');
  label('company_address','Company Address');label('po_no','Customer PO');
  label('rounded_total',frm.doc.disable_rounded_total?'Rounded Total':'Payable Total');
  label('grand_total',frm.doc.disable_rounded_total?'Payable Total':'Grand Total');
  const check=frm.fields_dict.set_posting_time?.$wrapper;
  check?.attr('title','Edit Posting Date and Time').find('input[type="checkbox"]').attr('aria-label','Edit Posting Date and Time');
 };
 ['Quotation','Sales Order','Sales Invoice'].forEach(dt=>frappe.ui.form.on(dt,{setup:prepare,before_load:prepare,onload:prepare,refresh:decorate,onload_post_render:decorate,disable_rounded_total:decorate}));
 frappe.ui.form.on('Stock Entry',{refresh:frm=>frm.fields_dict.set_posting_time?.$wrapper.attr('title','Edit Posting Date and Time').find('input[type="checkbox"]').attr('aria-label','Edit Posting Date and Time')});
})();

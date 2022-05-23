$(document).ready(function() {
	let table = document.getElementById("#posts");
	for(int i = 1; i < table.rows.length; i++) {
		$("#rButton"+i).click(function() {
			showReply(i);
		});
	}
	
	function showReply(num) {
		document.getElementById('#reply' + num).style.display = 'block';
	}
});
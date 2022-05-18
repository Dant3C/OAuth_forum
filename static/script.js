$(document).ready(function() {
	var rowCount = $('#posts tr').length;
	for(int i = 1, i < 3, i++) {
		$("#rButton"+n).click(function() {
			showReply(i):
		});
	}
	
	function showReply(num) {
		document.getElementById('reply' + num).style.display = 'block';
	}
}
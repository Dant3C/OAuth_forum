$(document).ready(function() {
	var rowCount = $('#posts tr').length;
	for(int i = 1, i < rowCount, i++)
		function showReply() {
			document.getElementById('reply' + i).style.display = 'block';
		}
	}
}
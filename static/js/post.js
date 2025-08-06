
const likeBtn = document.getElementById('likeBtn');
const likeCount = document.getElementById('likeCount');
const toast = document.getElementById('toast');


updateLikeButton();

function updateLikeButton() {
    if (isLiked) {
        likeBtn.classList.add('liked');
    } else {
        likeBtn.classList.remove('liked');
    }
    likeCount.textContent = currentLikeCount;
}

async function toggleLike() {
    likeBtn.disabled = true;

    try {
        const response = await fetch('/toggle_like', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                postid: postId
            })
        });

        const data = await response.json();

        if (data.success) {
            isLiked = data.liked;
            currentLikeCount = data.like_count;
            updateLikeButton();
            showToast(data.message);
        } else {
            showToast('Error: ' + data.message);
        }
    } catch (error) {
        console.error('Error toggling like:', error);
        showToast('Error occurred while toggling like');
    } finally {
        likeBtn.disabled = false;
    }
}

function showToast(message) {
    toast.textContent = message;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
async function refreshLikeStatus() {
    try {
        const response = await fetch(`/get_like_status/${postId}`);
        const data = await response.json();
        
        if (data.success) {
            isLiked = data.liked;
            currentLikeCount = data.like_count;
            updateLikeButton();
        }
    } catch (error) {
        console.error('Error refreshing like status:', error);
    }
}

function answerAndRedirect() {
    document.getElementById("answerOverlay").classList.add("show");
}

function closeAnswerModal() {
    document.getElementById("answerOverlay").classList.remove("show");
}

const answerTextarea = document.getElementById("answerTextarea");
const answerCharCount = document.getElementById("answerCharCount");

answerTextarea.addEventListener("input", () => {
    const len = answerTextarea.value.length;
    answerCharCount.textContent = `${len} / 500`;
    answerCharCount.className = "character-count";
    if (len > 400 && len <= 500) answerCharCount.classList.add("warning");
    if (len > 500) answerCharCount.classList.add("error");
});

function submitAnswer() {
    const text = answerTextarea.value.trim();
    if (!text) {
        showMessage("Answer cannot be empty", "error");
        return;
    }

    fetch(`/post/${postId}/answer`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ answer: text })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showMessage(data.message, "success");

            answerTextarea.value = "";
            answerCharCount.textContent = "0 / 500";

            setTimeout(() => location.reload(), 800);
        } else {
            showMessage(data.message, "error");
        }
    });
}
function showMessage(msg, type) {
    const box = document.getElementById("answerMessageBox");
    box.textContent = msg;
    box.className = `message ${type}`;
    box.style.display = "block";
}


refreshLikeStatus();
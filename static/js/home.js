const spotlightOverlay = document.getElementById('spotlightOverlay');
const openSpotlightBtn = document.getElementById('openSpotlight');
const cancelBtn = document.getElementById('cancelBtn');
const postBtn = document.getElementById('postBtn');
const postTextarea = document.getElementById('postTextarea');
const characterCount = document.getElementById('characterCount');
const messageBox = document.getElementById('messageBox');
const toast = document.getElementById('toast');

// Spotlight Modal Functions
openSpotlightBtn.addEventListener('click', () => {
    spotlightOverlay.classList.add('show');
    setTimeout(() => postTextarea.focus(), 300);
});

function closeModal() {
    spotlightOverlay.classList.remove('show');
    setTimeout(() => {
        postTextarea.value = '';
        updateCharacterCount();
        hideMessage();
        resetPostButton();
    }, 300);
}

spotlightOverlay.addEventListener('click', (e) => {
    if (e.target === spotlightOverlay) {
        closeModal();
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && spotlightOverlay.classList.contains('show')) {
        closeModal();
    }
});

cancelBtn.addEventListener('click', closeModal);

function updateCharacterCount() {
    const count = postTextarea.value.length;
    characterCount.textContent = `${count} / 500`;
    
    characterCount.classList.remove('warning', 'error');
    if (count > 450) {
        characterCount.classList.add('error');
    } else if (count > 400) {
        characterCount.classList.add('warning');
    }
}

postTextarea.addEventListener('input', updateCharacterCount);

function showMessage(text, type) {
    messageBox.textContent = text;
    messageBox.className = `message ${type}`;
    messageBox.style.display = 'block';
}

function hideMessage() {
    messageBox.style.display = 'none';
}

function setPostButtonLoading(loading) {
    postBtn.classList.toggle('loading', loading);
    postBtn.disabled = loading;
    
    if (loading) {
        postBtn.querySelector('.btn-text').textContent = 'Posting...';
    } else {
        postBtn.querySelector('.btn-text').textContent = 'Post';
    }
}

function resetPostButton() {
    setPostButtonLoading(false);
}

postBtn.addEventListener('click', async () => {
    const postText = postTextarea.value.trim();
    
    if (!postText) {
        showMessage('Please enter a valid Text!', 'error');
        return;
    }

    if (postText.length > 500) {
        showMessage('the text is too long (max. 500)', 'error');
        return;
    }

    setPostButtonLoading(true);
    hideMessage();

    try {
        const response = await fetch('/create_post', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                posttext: postText
            })
        });

        const data = await response.json();

        if (data.success) {
            showMessage('Post created! 🎉', 'success');
            setTimeout(() => {
                location.reload(); // Reload to show new post
            }, 1000);
        } else {
            showMessage(data.message || 'Error while creating Post:', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showMessage('Backend Server is not responding...', 'error');
    } finally {
        setPostButtonLoading(false);
    }
});

postTextarea.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        postBtn.click();
    }
});

// Like Functions
async function toggleLike(postId, likeButton) {
    likeButton.disabled = true;

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
            // Update the like button appearance
            if (data.liked) {
                likeButton.classList.add('liked');
            } else {
                likeButton.classList.remove('liked');
            }
            
            // Update the like count
            const likeCountElement = likeButton.querySelector('.like-count');
            likeCountElement.textContent = data.like_count;
            
            // Show toast notification
            showToast(data.message);
        } else {
            showToast('Error: ' + data.message);
        }
    } catch (error) {
        console.error('Error toggling like:', error);
        showToast('Error occurred while toggling like');
    } finally {
        likeButton.disabled = false;
    }
}

function showToast(message) {
    toast.textContent = message;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Initialize character count
updateCharacterCount();